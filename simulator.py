"""Synthetic terrain, bounded planning and a stop/sense/replan mission.
Geometric teaching model only: no soil, wheel dynamics or articulated ACE.
"""
import heapq
import json
import math
import random
import time

N = 36
DEFAULTS = dict(width=1.2, margin=0.2, clearance=0.45, slope=25,
                expansions=1800, milliseconds=250, score=150)
MODES = ("distance", "terrain", "quick")

def settings(raw):
    cfg = dict(DEFAULTS)
    limits = dict(width=(0.2,4), margin=(0,1), clearance=(0.05,2),
                  slope=(1,45), expansions=(1,5000),
                  milliseconds=(1,2000), score=(1,2000))
    for key, value in raw.items():
        if key not in limits or type(value) not in (int,float) or not math.isfinite(value):
            raise ValueError("Invalid rover settings")
        lo, hi = limits[key]
        if not lo <= value <= hi:
            raise ValueError("Setting outside supported range: " + key)
        cfg[key] = value
    if int(cfg["expansions"]) != cfg["expansions"]:
        raise ValueError("Expansion budget must be an integer")
    return cfg

def endpoint(p):
    if (not isinstance(p, list) or len(p)!=2 or
            any(type(v) is not int or not 0<=v<N for v in p)):
        raise ValueError("Coordinates must be integers from 0 to 35")
    return tuple(p)

def terrain(seed):
    rng = random.Random(seed)
    waves = [(rng.uniform(0.2,0.65),rng.uniform(.07,.2),
              rng.uniform(.07,.2),rng.uniform(0,6.28)) for _ in range(4)]
    craters = [(rng.uniform(9,27),rng.uniform(7,29),rng.uniform(3,5),
                rng.uniform(.7,1.5)) for _ in range(3)]
    def height(x,y):
        h = sum(a*math.sin(x*fx+y*fy+p) for a,fx,fy,p in waves)
        for cx,cy,r,d in craters:
            q=math.hypot(x-cx,y-cy)/r
            h += -d*math.exp(-q*q*2)+.35*d*math.exp(-((q-1)/.22)**2)
        return h
    coarse = [[height(x,y) for x in range(N)] for y in range(N)]
    truth = [row[:] for row in coarse]
    # Small pits intentionally absent from the initial mapping product.
    pits=[(18,18,1.0,1.1)]
    pits += [(rng.uniform(6,30),rng.uniform(6,30),rng.uniform(.65,1.2),
              rng.uniform(.7,1.4)) for _ in range(8)]
    for y in range(N):
        for x in range(N):
            for cx,cy,r,d in pits:
                truth[y][x] -= d*math.exp(-((x-cx)**2+(y-cy)**2)/(r*r))
    rocks=[]
    for _ in range(5):
        cx,cy=rng.uniform(7,29),rng.uniform(4,32)
        for _ in range(4):
            x,y=cx+rng.uniform(-2,2),cy+rng.uniform(-2,2)
            if min(math.hypot(x-3,y-18),math.hypot(x-32,y-18))>3:
                rocks.append([x,y,rng.uniform(.25,.65)])
    return dict(known=coarse, truth=truth, rocks=rocks,
                observed=[[False]*N for _ in range(N)], seed=seed)

def reveal(world, pos, radius=4):
    changed=0
    for y in range(N):
        for x in range(N):
            if math.hypot(x-pos[0],y-pos[1])<=radius:
                if not world["observed"][y][x]:
                    changed += abs(world["known"][y][x]-world["truth"][y][x])>.03
                world["known"][y][x]=world["truth"][y][x]
                world["observed"][y][x]=True
    return changed

def segment_distance(p,a,b):
    vx,vy=b[0]-a[0],b[1]-a[1]
    denom=vx*vx+vy*vy
    t=max(0,min(1,((p[0]-a[0])*vx+(p[1]-a[1])*vy)/denom)) if denom else 0
    return math.hypot(p[0]-a[0]-t*vx,p[1]-a[1]-t*vy)

class Safety:
    def __init__(self, heights, rocks, cfg):
        self.h,self.rocks,self.cfg=heights,rocks,cfg
        self.n=len(heights)
        self.radius=cfg["width"]/2+cfg["margin"]
        self.cache={}
        self.slopes=[]
        for y in range(self.n):
            row=[]
            for x in range(self.n):
                gx,gy=self.gradient(x,y)
                row.append(math.degrees(math.atan(math.hypot(gx,gy))))
            self.slopes.append(row)

    def gradient(self,x,y):
        n=self.n
        xa,xb=max(0,x-1),min(n-1,x+1)
        ya,yb=max(0,y-1),min(n-1,y+1)
        return ((self.h[y][xb]-self.h[y][xa])/max(1,xb-xa),
                (self.h[yb][x]-self.h[ya][x])/max(1,yb-ya))

    def check(self,a,b):
        key=(tuple(a),tuple(b))
        if key in self.cache:
            return self.cache[key]
        value=self._check(a,b)
        self.cache[key]=value
        return value

    def _check(self,a,b):
        r,n=self.radius,self.n
        if any(v-r<-.5 or v+r>n-.5 for p in (a,b) for v in p):
            return "BOUNDARY",0,0
        for x,y,rr in self.rocks:
            if segment_distance((x,y),a,b)<=r+rr:
                return "ROCK_CLEARANCE",0,0
        # Include every raster cell intersecting a conservative swept bounding box.
        xa=max(0,math.ceil(min(a[0],b[0])-r-.5))
        xb=min(n-1,math.floor(max(a[0],b[0])+r+.5))
        ya=max(0,math.ceil(min(a[1],b[1])-r-.5))
        yb=min(n-1,math.floor(max(a[1],b[1])+r+.5))
        slope=max(self.slopes[y][x] for y in range(ya,yb+1) for x in range(xa,xb+1))
        # Relief relative to a local tangent plane, not absolute hill elevation.
        cx,cy=a
        gx,gy=self.gradient(cx,cy)
        residuals=[self.h[y][x]-(self.h[cy][cx]+gx*(x-cx)+gy*(y-cy))
                   for y in range(ya,yb+1) for x in range(xa,xb+1)]
        relief=max(residuals)-min(residuals)
        if slope>self.cfg["slope"]:
            return "SLOPE",slope,relief
        if relief>self.cfg["clearance"]:
            return "GROUND_CLEARANCE_PROXY",slope,relief
        return None,slope,relief

    def cost(self,a,b):
        _,slope,relief=self.check(a,b)
        return math.dist(a,b)*(1+3*(slope/self.cfg["slope"])**2
                              +relief/self.cfg["clearance"])

def search(safety,start,goal,mode,cfg,remaining=None):
    """Four-connected A*. Weighted A* uses w=2; budget failure is not no-path."""
    began=time.perf_counter()
    expanded=0
    rejected={}
    pruned=False
    def result(status,path=None):
        path=path or []
        score=sum(safety.cost(a,b) for a,b in zip(path,path[1:]))
        if status=="SUCCESS" and score>cap+1e-9:
            status="CANDIDATE_OVER_SCORE"
        return dict(mode=mode,status=status,path=path,distance=max(0,len(path)-1),
                    score=score,expanded=expanded,rejected=rejected,
                    planning_ms=(time.perf_counter()-began)*1000)
    cap=cfg["score"] if remaining is None else remaining
    for name,p in (("START",start),("GOAL",goal)):
        reason,_,_=safety.check(p,p)
        if reason:
            return result(name+"_"+reason)
    heuristic=lambda p: abs(p[0]-goal[0])+abs(p[1]-goal[1])
    weight=2 if mode=="quick" else 1
    frontier=[(weight*heuristic(start),0,start)]
    costs,parents,closed={start:0},{},set()
    for _ in range(4*safety.n*safety.n+1):
        if not frontier:
            return result("SCORE_LIMIT" if pruned else "NO_ROUTE")
        if (time.perf_counter()-began)*1000>=cfg["milliseconds"]:
            return result("TIME_BUDGET")
        _,g,p=heapq.heappop(frontier)
        if p in closed:
            continue
        if p==goal:
            path=[p]
            for _ in range(safety.n*safety.n):
                if path[-1]==start:
                    return result("SUCCESS",list(reversed(path)))
                path.append(parents[path[-1]])
            return result("INTERNAL_ERROR")
        if expanded>=cfg["expansions"]:
            return result("EXPANSION_BUDGET")
        expanded+=1
        closed.add(p)
        x,y=p
        for dx,dy in ((1,0),(0,1),(-1,0),(0,-1)):
            q=x+dx,y+dy
            if not (0<=q[0]<safety.n and 0<=q[1]<safety.n):
                continue
            reason,_,_=safety.check(p,q)
            if reason:
                rejected[reason]=rejected.get(reason,0)+1
                continue
            step=1 if mode=="distance" else safety.cost(p,q)
            new=g+step
            if mode!="distance" and new>cap:
                pruned=True
                continue
            if q not in closed and new<costs.get(q,float("inf")):
                costs[q],parents[q]=new,p
                heapq.heappush(frontier,(new+weight*heuristic(q),new,q))
    return result("INTERNAL_ERROR")

class Mission:
    def __init__(self,seed):
        self.world=terrain(seed)
        self.cfg=settings({})
        self.pos=(3,18)
        self.goal=(32,18)
        self.path=[]
        self.results=[]
        self.mode="terrain"
        self.spent=0
        self.travel=0
        self.replans=0
        self.discoveries=0
        self.stopped=True

    def snapshot(self,event,**extra):
        return dict(event=event,world=self.world,position=self.pos,goal=self.goal,
                    path=self.path,spent=self.spent,travel=self.travel,
                    replans=self.replans,discoveries=self.discoveries,**extra)

    def compare(self,request):
        self.cfg=settings(request["settings"])
        self.pos=endpoint(request["start"])
        self.goal=endpoint(request["goal"])
        self.spent=self.travel=self.replans=self.discoveries=0
        self.stopped=True
        self.path=[]
        # Reset knowledge to initial map for a fair, repeatable new mission.
        self.world=terrain(self.world["seed"])
        self.discoveries=reveal(self.world,self.pos)
        began=time.perf_counter()
        self.results=[]
        for mode in MODES:
            # Fresh identical caches so later planners do not benefit from earlier work.
            safety=Safety(self.world["known"],self.world["rocks"],self.cfg)
            self.results.append(search(safety,self.pos,self.goal,mode,self.cfg))
        return self.snapshot("COMPARED",results=self.results,
                             comparison_ms=(time.perf_counter()-began)*1000)

    def select(self,mode):
        if mode not in MODES:
            raise ValueError("Unknown planner")
        candidate=next((r for r in self.results if r["mode"]==mode),None)
        if not candidate or candidate["status"]!="SUCCESS":
            raise ValueError("Select a successful candidate")
        self.mode=mode
        self.path=[tuple(p) for p in candidate["path"]]
        self.stopped=False
        return self.snapshot("SELECTED")

    def step(self):
        if self.stopped:
            return self.snapshot("STOPPED")
        if self.pos==self.goal:
            self.stopped=True
            return self.snapshot("ARRIVED")
        changed=reveal(self.world,self.pos)
        self.discoveries+=changed
        safety=Safety(self.world["known"],self.world["rocks"],self.cfg)
        # Re-evaluate remaining route when new terrain is measured.
        invalid=any(safety.check(a,b)[0] for a,b in zip(self.path,self.path[1:]))
        if invalid or len(self.path)<2:
            self.replans+=1
            if self.replans>20:
                self.stopped=True
                return self.snapshot("REPLAN_LIMIT")
            r=search(safety,self.pos,self.goal,self.mode,self.cfg,self.cfg["score"]-self.spent)
            if r["status"]!="SUCCESS":
                self.stopped=True
                return self.snapshot("REPLAN_"+r["status"],last_plan=r)
            self.path=[tuple(p) for p in r["path"]]
            return self.snapshot("REPLANNED",last_plan=r)
        nxt=self.path[1]
        # Simulator-side truth guard stops before a missed geometric hazard.
        truth=Safety(self.world["truth"],self.world["rocks"],self.cfg)
        reason,_,_=truth.check(self.pos,nxt)
        if reason:
            self.stopped=True
            return self.snapshot("UNSEEN_HAZARD_STOP",reason=reason)
        cost=truth.cost(self.pos,nxt)
        if self.spent+cost>self.cfg["score"]+1e-9:
            self.stopped=True
            return self.snapshot("MISSION_SCORE_LIMIT")
        self.spent+=cost
        self.travel+=1
        self.pos=nxt
        self.path=self.path[1:]
        return self.snapshot("MOVED",new_details=changed)

mission=None

def dispatch(payload):
    global mission
    try:
        r=json.loads(payload)
        op=r["op"]
        if op=="generate":
            seed=r.get("seed",42)
            if type(seed) is not int or not 0<=seed<=999999:
                raise ValueError("Seed must be an integer from 0 to 999999")
            mission=Mission(seed)
            out=mission.snapshot("GENERATED")
        elif mission is None:
            raise ValueError("Generate terrain first")
        elif op=="compare":
            out=mission.compare(r)
        elif op=="select":
            out=mission.select(r["mode"])
        elif op=="step":
            out=mission.step()
        else:
            raise ValueError("Unknown operation")
        return json.dumps(out,allow_nan=False)
    except (ValueError,KeyError,TypeError) as e:
        return json.dumps(dict(event="INVALID_INPUT",message=str(e)))

