# Copyright (C) 2002, Thomas Hamelryck (thamelry@vub.ac.be)
# This code is part of the Biopython distribution and governed by its
# license.  Please see the LICENSE file that should have been included
# as part of this package.


from Numeric import array, sum, sqrt, arccos
from LinearAlgebra import determinant


def angle(v1, v2, v3):
    """
    Calculate the angle between 3 vectors
    representing 3 connected points.
    """
    v1=v1-v2
    v3=v3-v2
    return v1.angle(v3)


def dihedral(v1, v2, v3, v4):
    """
    Calculate the dihedral angle between 4 vectors
    representing 4 connected points. The angle is in
    ]-pi, pi].
    """
    ab=v1-v2
    cb=v3-v2
    db=v4-v3
    u=ab**cb
    v=db**cb
    w=u**v
    angle=u.angle(v)
    # Determine sign of angle
    try:
        if cb.angle(w)>0.001:
            angle=-angle
    except ZeroDivisionError:
        # dihedral=pi
        pass
    return angle


class Vector:
    "3D vector."

    def __init__(self, x, y, z):
        self._ar=array((x, y, z), 'd')
        self._norm=None

    def __add__(self, other):
        "Add a vector or a scalar"
        if not isinstance(other, Vector):
            x,y,z=self._ar+other
        else:
            x,y,z=self._ar+other._ar
        return Vector(x,y,z)

    def __sub__(self, other):
        "Substract a vector or a scalar"
        if not isinstance(other, Vector):
            x,y,z=self._ar-other
        else:
            x,y,z=self._ar-other._ar
        return Vector(x,y,z)

    def __mul__(self, other):
        "Dot product"
        if not isinstance(other, Vector):
            return sum(self._ar*other)
        else:
            return sum(self._ar*other._ar)

    def __div__(self, a):
        "Divide by a scalar"
        x,y,z=self._ar/a
        return Vector(x,y,z)

    def __pow__(self, other):
        "Cross product"
        a,b,c=self._ar
        d,e,f=other._ar
        c1=determinant(array(((b,c), (e,f))))
        c2=determinant(array(((a,c), (d,f))))
        c3=determinant(array(((a,b), (d,e))))
        return Vector(c1,c2,c3)

    def __str__(self):
        x,y,z=self._ar
        return "<Vector %.2f %.2f %.2f>" % (x,y,z)

    def norm(self):
        "Return vector norm"
        if self._norm is None:
            self._norm=sqrt(sum(self._ar*self._ar))
        return self._norm

    def normalize(self):
        "Normalize the vector"
        self._ar=self._ar/self.norm()

    def angle(self, other):
        "Angle between two vectors"
        n1=self.norm()
        n2=other.norm()
        c=(self*other)/(n1*n2)
        return arccos(c)

    def get_array(self):
        "Return array of coordinates"
        return self._ar

if __name__=="__main__":

        from math import pi

        v1=Vector(0,0,1)
        v2=Vector(0,0,0)
        v3=Vector(1,0,0)
        v4=Vector(1,-1,0)

        print angle(v1, v2, v3)
        print dihedral(v1, v2, v3, v4)
        print 180*dihedral(v1, v2, v3, v4)/pi


        
        
