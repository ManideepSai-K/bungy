import unittest
from planner import plan

class PlannerTests(unittest.TestCase):
    def test_shortest(self):
        r=plan([[0]*4 for _ in range(4)], [0,0], [3,3])
        self.assertEqual(r["distance_m"],6)
        self.assertEqual(r["path"][0],(0,0))
        self.assertEqual(r["path"][-1],(3,3))
    def test_sealed(self):
        self.assertEqual(plan([[0,1,0]]*3,[0,0],[2,2])["status"],"NO_ROUTE")
    def test_blocked(self):
        self.assertEqual(plan([[1,0]],[0,0],[1,0])["status"],"START_BLOCKED")
    def test_budget(self):
        self.assertEqual(plan([[0]*5 for _ in range(5)],[0,0],[4,4],1)["status"],"BUDGET_EXCEEDED")
    def test_no_diagonal_squeeze(self):
        self.assertEqual(plan([[0,1],[1,0]],[0,0],[1,1])["status"],"NO_ROUTE")
    def test_same_position(self):
        self.assertEqual(plan([[0]],[0,0],[0,0])["distance_m"],0)
    def test_invalid(self):
        for grid in ([],[[0],[0,0]],[[2]],[[False]]):
            self.assertEqual(plan(grid,[0,0],[0,0])["status"],"INVALID_MAP")
    def test_outside(self):
        self.assertEqual(plan([[0]],[-1,0],[0,0])["status"],"START_OUT_OF_BOUNDS")
    def test_deterministic_and_safe(self):
        grid=[[0]*12 for _ in range(12)]
        for y in range(12):
            grid[y][6]=int(y!=5)
        a=plan(grid,[1,9],[10,2]);b=plan(grid,[1,9],[10,2])
        self.assertEqual(a["status"],"SUCCESS")
        self.assertEqual(a["path"],b["path"])
        for x,y in a["path"]: self.assertEqual(grid[y][x],0)
        for (x,y),(u,v) in zip(a["path"],a["path"][1:]):
            self.assertEqual(abs(x-u)+abs(y-v),1)

if __name__=="__main__": unittest.main()
