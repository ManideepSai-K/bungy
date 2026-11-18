import json
import math
import unittest
from unittest.mock import patch
from simulator import (Mission, Safety, terrain, reveal, search, settings, dispatch)

class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.cfg=settings({"milliseconds":2000})
        self.flat=[[0.0]*12 for _ in range(12)]

    def test_seed_reproducibility(self):
        self.assertEqual(terrain(42),terrain(42))
        self.assertNotEqual(terrain(42)["truth"],terrain(43)["truth"])

    def test_hidden_pits_and_sensor(self):
        w=terrain(42)
        self.assertNotEqual(w["known"][18][18],w["truth"][18][18])
        before=w["known"][18][18]
        reveal(w,(3,18))
        self.assertEqual(w["known"][18][18],before)
        self.assertGreater(reveal(w,(18,18)),0)
        self.assertEqual(w["known"][18][18],w["truth"][18][18])

    def test_clearance_increases_with_width(self):
        rocks=[[5,3.4,.1]]
        narrow=Safety(self.flat,rocks,settings({"width":.2,"margin":0}))
        wide=Safety(self.flat,rocks,settings({"width":2,"margin":.2}))
        self.assertIsNone(narrow.check((4,4),(5,4))[0])
        self.assertEqual(wide.check((4,4),(5,4))[0],"ROCK_CLEARANCE")

    def test_swept_rock_between_waypoints(self):
        s=Safety(self.flat,[[4.5,4,.1]],settings({"width":.2,"margin":0}))
        self.assertIsNone(s.check((4,4),(4,4))[0])
        self.assertIsNone(s.check((5,4),(5,4))[0])
        self.assertEqual(s.check((4,4),(5,4))[0],"ROCK_CLEARANCE")

    def test_slope_and_boundary(self):
        ramp=[[x*.7 for x in range(12)] for _ in range(12)]
        self.assertEqual(Safety(ramp,[],self.cfg).check((4,4),(5,4))[0],"SLOPE")
        self.assertEqual(Safety(self.flat,[],self.cfg).check((0,0),(1,0))[0],"BOUNDARY")

    def test_clearance_relief_not_absolute_height(self):
        shifted=[[h+100 for h in row] for row in self.flat]
        a=Safety(self.flat,[],self.cfg).check((4,4),(5,4))
        b=Safety(shifted,[],self.cfg).check((4,4),(5,4))
        self.assertEqual(a,b)
        self.flat[4][5]=.3
        s=Safety(self.flat,[],settings({"clearance":.05,"slope":45}))
        self.assertEqual(s.check((4,4),(5,4))[0],"GROUND_CLEARANCE_PROXY")

    def test_flat_optimum_and_same_endpoint(self):
        for mode in ("distance","terrain","quick"):
            s=Safety(self.flat,[],self.cfg)
            r=search(s,(2,2),(8,8),mode,self.cfg)
            self.assertEqual(r["status"],"SUCCESS")
            self.assertEqual(r["distance"],12)
            self.assertEqual(r["score"],12)
            self.assertEqual(search(s,(2,2),(2,2),mode,self.cfg)["distance"],0)

    def test_no_route_distinct_from_budgets(self):
        rocks=[[6,y,.6] for y in range(12)]
        r=search(Safety(self.flat,rocks,self.cfg),(2,5),(9,5),"terrain",self.cfg)
        self.assertEqual(r["status"],"NO_ROUTE")
        cfg=settings({"expansions":1})
        r=search(Safety(self.flat,[],cfg),(2,2),(8,8),"terrain",cfg)
        self.assertEqual(r["status"],"EXPANSION_BUDGET")
        with patch("simulator.time.perf_counter",side_effect=[0,10,10]):
            r=search(Safety(self.flat,[],self.cfg),(2,2),(8,8),"terrain",self.cfg)
        self.assertEqual(r["status"],"TIME_BUDGET")

    def test_score_limit_and_candidate_rejection(self):
        cfg=settings({"score":5,"milliseconds":2000})
        for mode,status in (("terrain","SCORE_LIMIT"),("distance","CANDIDATE_OVER_SCORE")):
            r=search(Safety(self.flat,[],cfg),(2,2),(8,8),mode,cfg)
            self.assertEqual(r["status"],status)

    def test_default_routes_and_execution(self):
        m=Mission(42)
        r=m.compare(dict(settings={"milliseconds":2000},start=[3,18],goal=[32,18]))
        bymode={v["mode"]:v for v in r["results"]}
        self.assertTrue(all(v["status"]=="SUCCESS" for v in r["results"]))
        self.assertLessEqual(bymode["distance"]["distance"],bymode["terrain"]["distance"])
        self.assertLessEqual(bymode["terrain"]["score"],bymode["distance"]["score"])
        m.select("terrain")
        for _ in range(200):
            old=m.pos
            result=m.step()
            if result["event"]=="MOVED":
                s=Safety(m.world["truth"],m.world["rocks"],m.cfg)
                self.assertIsNone(s.check(old,m.pos)[0])
            if m.stopped:
                break
        self.assertEqual(result["event"],"ARRIVED")
        self.assertGreater(m.replans,0)
        self.assertLessEqual(m.spent,m.cfg["score"])

    def test_truth_guard_stops_without_movement(self):
        m=Mission(42)
        m.world["known"]=[[0.0]*36 for _ in range(36)]
        m.world["truth"]=[[0.0]*36 for _ in range(36)]
        m.world["truth"][18][4]=-2
        m.world["rocks"]=[]
        m.pos=(3,18);m.goal=(5,18);m.path=[(3,18),(4,18),(5,18)];m.stopped=False
        with patch("simulator.reveal",return_value=0):
            r=m.step()
        self.assertEqual(r["event"],"UNSEEN_HAZARD_STOP")
        self.assertEqual(m.pos,(3,18))
        self.assertEqual(m.spent,0)

    def test_mission_budget_stops_before_move(self):
        m=Mission(42)
        m.world["known"]=[[0.0]*36 for _ in range(36)]
        m.world["truth"]=[[0.0]*36 for _ in range(36)]
        m.world["rocks"]=[]
        m.path=[(3,18),(4,18)];m.spent=149.5;m.stopped=False
        self.assertEqual(m.step()["event"],"MISSION_SCORE_LIMIT")
        self.assertEqual(m.pos,(3,18))

    def test_input_validation(self):
        for cfg in ({"width":-1},{"slope":float("nan")},{"expansions":1.5}):
            with self.assertRaises(ValueError):settings(cfg)
        self.assertEqual(json.loads(dispatch('{"op":"generate","seed":-1}'))["event"],"INVALID_INPUT")

if __name__=="__main__":
    unittest.main()

