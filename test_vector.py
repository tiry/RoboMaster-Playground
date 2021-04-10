import unittest
from vector import Vector

class TestVectors(unittest.TestCase):

    def test_accessXYZ(self):
        v1 = Vector(1,2,3)

        self.assertEqual(1, v1.x)
        self.assertEqual(1, v1[0])        
        self.assertEqual(2, v1.y)
        self.assertEqual(2, v1[1])
        self.assertEqual(3, v1.z)
        self.assertEqual(3, v1[2])

        v1.x=-1
        self.assertEqual(-1, v1.x)
       
    def test_sum(self):

        v1 = Vector(1,2,3)
        v2 = Vector(3,4,5)
        
        v3=v1+v2
        self.assertEqual(4, v3.x)
        self.assertEqual(6, v3.y)
        self.assertEqual(8, v3.z)

    def test_scale(self):

        v1 = Vector(2,2,2)
        v2 = Vector(1,2,3)
        v3 = v1.scale(v2)

        self.assertEqual(2, v3.x)
        self.assertEqual(4, v3.y)
        self.assertEqual(6, v3.z)
    

    def test_round(self):

        v1 = Vector(0.2,0.02,0.002)
        v2 = v1.round(2)

        self.assertEqual(0.2, v2.x)
        self.assertEqual(0.02, v2.y)
        self.assertEqual(0, v2.z)
    

if __name__ == "__main__":
  print("running tests")
  unittest.main()
