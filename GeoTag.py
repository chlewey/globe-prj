
import xml.etree.ElementTree as ET
from toolkit import collector, attributer, np, re

class GeoTag(collector, attributer):
    _svg_attribs = ['stroke', 'stroke-width', 'fill']  # Add SVG attributes
    _kml_attribs = ['color', 'width']  # Add KML attributes
    _kml_placemark_attribs = ['visibility', 'altitudeMode', 'drawOrder']  # Add KML placemark attributes
    
    def __init__(self, name, id=None, description=None, **kwargs):
        self._name = name
        self._description = description
        collector.__init__(self, id or self.simplify_name(name))
        attributer.__init__(self, **kwargs)

    def _valid_key(self, key):
        return key in self._svg_attribs + self._kml_attribs
    
    @property
    def name(self):
        return self._name
    
    @property
    def id(self):
        return self._id
    
    @property
    def description(self):
        return self._description
    
    @name.setter
    def name(self, value):
        self._name = str(value)
    
    @description.setter
    def description(self, value):
        self._description = str(value)
    
    @id.setter
    def id(self, value):
        del GeoTag._ids[self._id]
        self._id = self._set_id(value)
    
    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}:{self.__str__()}>'
    
    def __str__(self):
        return f'[{self.__class__.__name__} {self.id}]'
    
    def svg_element(self, tag, **kwargs):
        element = ET.Element(tag)
        element.set('id', self.id)
        attributes = {key: value for key, value in self._attributes.items() if key in self._svg_attribs}
        attributes.update(kwargs)
        for attribute, value in attributes.items():
            element.set(attribute, str(value))
        return element
    
    def kml_element(self, tag='Placemark', **kwargs):
        placemark = ET.Element(tag)
        placemark.set('id', self.id)
        attributes = {key: value for key, value in self._attributes.items() if key in self._kml_attribs}
        attributes.update(kwargs)
        
        for attribute in self._kml_placemark_attribs:
            if attribute in attributes:
                placemark.set(attribute, attributes.pop(attribute))
        if self.description:
            description = ET.SubElement(placemark, 'description')
            description.text = self.description
        if "style" in attributes:
            style = ET.SubElement(placemark, 'styleUrl')
            style.text = '#' + attributes.pop("style")
        if attributes:
            extension = ET.SubElement(placemark, 'ExtendedData')
            for attribute, value in attributes.items():
                item = ET.SubElement(extension, 'Data')
                item.set('name', attribute)
                item_value = ET.SubElement(item, 'value')
                item_value.text = str(value)
        return placemark
    
    def as_svg(self, projection=None, **kwargs):
        raise NotImplementedError(f'{self.__class__.__name__} does not have .as_svg() method')
    
    def as_kml(self, **kwargs):
        raise NotImplementedError(f'{self.__class__.__name__} does not have .as_kml() method')
    
class Point3D(object):
    def __init__(self, x, y, z):
        self._arg = np.array([x, y, z], dtype=float)
        super().__init__()
    
    @classmethod
    def from_point(cls, point, radius=None):
        assert len(point) == 3
        x, y, z = point
        if not radius:
            return cls(x, y, z)
        r = np.sqrt(x**2 + y**2 + z**2)
        return cls(x * radius / r, y * radius / r, z * radius / r)
    
    @classmethod
    def from_polar(clas, theta, phi, radius=1.0):
        return clas(radius * np.cos(theta) * np.cos(phi), radius * np.sin(phi), radius * np.sin(theta) * np.cos(phi))
    
    @property
    def x(self):
        return self._arg[0]
    
    @property
    def y(self):
        return self._arg[1]
    
    @property
    def z(self):
        return self._arg[2]
    
    @property
    def theta(self):
        return np.arctan2(self.z, self.x)
    
    @property
    def rho(self):
        return np.sqrt(self.x**2 + self.z**2)
    
    @property
    def phi(self):
        return np.arctan2(self.y, self.rho)
    
    def square(self):
        return self.x**2 + self.y**2 + self.z**2
    
    @property
    def radius(self):
        return np.sqrt(self.square())
    
    def __abs__(self):
        return np.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def __rmul__(self, scalar):
        return Point3D(scalar*self.x, scalar*self.y, scalar*self.z)
    
    def __mul__(self, scalar):
        return Point3D(self.x*scalar, self.y*scalar, self.z*scalar)
    
    def __truediv__(self, scalar):
        return Point3D(self.x/scalar, self.y/scalar, self.z/scalar)
    
    def __imul__(self, scalar):
        self._arg *= scalar
        return self
    
    def __itruediv__(self, scalar):
        self._arg /= scalar
        return self
    
    def __iadd__(self, other):
        self._arg += other._arg
        return self
    
    def __add__(self, other):
        return Point3D(self.x+other.x, self.y+other.y, self.z+other.z)
    
    def __isub__(self, other):
        self._arg -= other._arg
        return self
    
    def __sub__(self, other):
        return Point3D(self.x-other.x, self.y-other.y, self.z-other.z)
    
    def cross(self, other):
        return Point3D(self.y*other.z - self.z*other.y, self.z*other.x - self.x*other.z, self.x*other.y - self.y*other.x)
    
    def dot(self, other):
        return self.x*other.x + self.y*other.y + self.z*other.z
    
    def __tuple__(self):
        return tuple(self._arg)
    
    def __len__(self):
        return len(self._arg)
    
    def __getindex__(self, index):
        assert 0 <= index < len(self._arg)
        return self._arg[index]
    
    def __str__(self):
        return str(tuple(self._arg))
    
    def __format__(self, fmt):
        if fmt == 's' or fmt == '':
            return self.__str__()
        
        match = re.match(r'([ _0])?([<>^])?(\d+)?(\.\d+)?([fgpPs])', fmt)
        if not match:
            raise ValueError(f'invalid format string: {fmt!r}')
        fill, alignment, width, precision, specifier = match.groups()
        if fill is None: fill=''
        if alignment is None: alignment=''
        if precision is None: precision=''
        
        if specifier=='g':
            return f'({self.x:g}, {self.y:g}, {self.z:g})'
        
        if specifier=='s':
            s = self.__str__()
            if width:
                return f'{s:{fill}{alignment}{width}s}'
            else:
                return s
        
        if specifier=='f':
            if width:
                swidth = (int(width)-6) // 3
                s = f'({self.x:{fill}{swidth}{precision}f}, {self.y:{fill}{swidth}{precision}f}, {self.z:{fill}{swidth}{precision}f})'
                return f'{s: {alignment}s}'
            elif precision:
                return f'({self.x:{precision}f}, {self.y:{precision}f}, {self.z:{precision}f})'
            else:
                return f'({self.x:f}, {self.y:f}, {self.z:f})'
        
        if specifier=='p':
            if width:
                swidth = (int(width)-5) // 3
                s = f'{self.radius:{fill}{swidth}{precision}f}@({self.theta:{fill}{swidth}{precision}f}; {self.phi:{fill}{swidth}{precision}f})'
                return f'{s: {alignment}s}'
            elif precision:
                return f'{self.radius:{precision}f}@({self.theta:{precision}f}; {self.phi:{precision}f})'
            else:
                return f'{self.radius:g}@({self.theta:g}; {self.phi:g})'
        
        if specifier=='P':
            lat = np.degrees(self.phi)
            lon = np.degrees(self.theta)
            if width:
                swidth = (int(width)-7) // 3
                s = f'{self.radius:{fill}{swidth}{precision}f}@({lon:{fill}{swidth}{precision}f}°; {lat:{fill}{swidth}{precision}f}°)'
                return f'{s: {alignment}s}'
            elif precision:
                return f'{self.radius:{precision}f}@({lon:{precision}f}°; {lat:{precision}f}°)'
            else:
                return f'{self.radius:g}@({lon:g}°; {lat:g}°)'
    
    @classmethod
    def zero(cls):
        return cls(0, 0, 0)
    
    @classmethod
    def i(cls):
        return cls(1, 0, 0)
    
    @classmethod
    def j(cls):
        return cls(0, 1, 0)
    
    @classmethod
    def k(cls):
        return cls(0, 0, 1)
    
class CoordinatePoint(Point3D):
    def __init__(self, long, lat):
        x = np.cos(np.radians(lat)) * np.cos(np.radians(long))
        y = np.sin(np.radians(lat))
        z = np.cos(np.radians(lat)) * np.sin(np.radians(long))
        super().__init__(x, y, z)
    
    @classmethod
    def from_point(cls, point):
        return cls(np.degree(point.theta), np.degree(point.phi))
    
    @property
    def longitude(self):
        return np.degrees(self.theta)
    
    @property
    def latitude(self):
        return np.degrees(self.phi)

    def __str__(self):
        return f'{self.longitude:g},{self.latitude:g}'
    
    def __format__(self, fmt):
        m = re.match(r'([ _0])?([<>^])?(\d+)?(\.\d+)?([fgpPrs])', fmt)
        if not m:
            raise ValueError(f'invalid format string: {fmt!r}')
        fill, alignment, width, precision, specifier = m.groups()
        
        if specifier == 's':
            # Call __str__ method and apply width, alignment, and fill
            formatted_str = str(self)
            if width:
                formatted_str = f'{formatted_str:{fill}{alignment}{width}}'
            return formatted_str
        
        if specifier == 'g':
            return f'({self.longitude:g}, {self.latitude:g})'
        if fill is None: fill=''
        if alignment is None: alignment=''
        if precision is None: precision=''
        
        if specifier == 'f':
            if width:
                swidth = (int(width) - 4) // 2
                s = f'({self.longitude:{fill}{swidth}{precision}f}, {self.latitude:{fill}{swidth}{precision}f})'
                return f'{s: {alignment}s}'
            elif precision:
                return f'({self.longitude:{precision}f}, {self.latitude:{precision}f})'
            else:
                return f'({self.longitude:f}, {self.latitude:f})'
        
        if specifier in ('p', 'P'):
            if width:
                swidth = (int(width) - 6) // 2
                s = f'({self.longitude:{fill}{swidth}{precision}f}°, {self.latitude:{fill}{swidth}{precision}f})°'
                return f'{s: {alignment}s}'
            elif precision:
                return f'({self.longitude:{precision}f}°, {self.latitude:{precision}f})°'
            else:
                return f'({self.longitude:f}°, {self.latitude:f})°'
        
        if specifier == 'r':
            if width:
                swidth = (int(width) - 4) // 2
                s = f'({self.theta:{fill}{swidth}{precision}f}, {self.phi:{fill}{swidth}{precision}f})'
                return f'{s: {alignment}s}'
            elif precision:
                return f'({self.theta:{precision}f}, {self.phi:{precision}f})'
            else:
                return f'({self.theta:f}, {self.phi:f})'
    
    @classmethod
    def kml_format(self, lon_precision=None, lat_precision=None):
        if lon_precision is None and lat_precision is None:
            return '{:g},{:g},0'
        if lat_precision is None:
            lat_precision = lon_precision
        elif lon_precision is None:
            lon_precision = lat_precision
        return '{{:.{}f}},{{:.{}f}},0'.format(lon_precision, lat_precision)

class CoordinateList:
    def __init__(self, closed=False, points=None):
        self._closed = closed
        self._points = [] if points is None else points
    
    @property
    def closed(self):
        return self._closed
    
    @closed.setter
    def closed(self, value):
        self._closed = bool(value)
    
    @property
    def points(self):
        return self._points
    
    def __len__(self):
        return len(self._points)
    
    def append(self, point):
        self._points.append(point)
    
    def extend(self, points):
        self._points.extend(points)
    
    def insert(self, index, point):
        self._points.insert(index, point)
    
    def remove(self, point):
        self._points.remove(point)
    
    def pop(self, index=-1):
        return self._points.pop(index)
    
    def index(self, point):
        return self._points.index(point)
    
    def reverse(self):
        self._points.reverse()
    
    def clear(self):
        self._points.clear()
    
    def copy(self):
        return CoordinateList(self._points.copy())
    
    def __getitem__(self, index):
        return self._points[index]
    
    def __setitem__(self, index, value):
        self._points[index] = value
    
    def __delitem__(self, index):
        del self._points[index]
    
    def append_list(self, other_list, from_index=None, reverse=False):
        if from_index is None:
            from_index = len(self._points) - 1
        
        if reverse:
            other_list = reversed(other_list)
        
        for point in other_list:
            self._points.insert(from_index, point)
    
    def append_list_coords(self, other_list, from_coords, reverse=False):
        try:
            index = self._points.index(from_coords)
        except ValueError:
            raise ValueError("Coordinates not found in the list.")
        
        self.append_list(other_list, index, reverse)
    
    def __str__(self):
        return "[" + ", ".join(map(str, self._points)) + "]"
    
    def __repr__(self):
        return f"CoordinateList({self._points})"
    
    def path_list(self, projection=None, precision=None):
        if projection is None:
            projection = lambda p: (p.longitude, p.latitude)
        format_str = "{},{}" if precision is None else "{{:.{}f}},{{:.{}f}}".format(precision, precision)
        
        coordinates = []
        for point in self._points:
            lon, lat = projection(point)
            coordinates.append(format_str.format(lon, lat))
        
        return "M " + " ".join(coordinates) + (" Z" if self.closed else "")
    
    def kml_list(self, separator=' ', lon_precision=None, lat_precision=None):
        format_str = CoordinatePoint.kml_format(lon_precision, lat_precision)
        
        items = []
        for point in self._points:
            item_str = format_str.format(point.longitude, point.latitude)
            items.append(item_str)
        if self.closed:
            items.append(format_str.format(self._points[0].longitude, self._points[0].latitude))
        
        return separator.join(items)
    
    def normal(self):
        points = self._points + [self._points[0]] if self.closed else self._points
        normal_vector = Point3D.zero()
        for i in range(len(points) - 1):
            normal_vector += points[i].cross(points[i + 1])
        return normal_vector

    
    def midpoint(self):
        normal_vec = self.normal()
        if abs(normal_vec) == 0:
            return None  # No meaningful midpoint if normal is zero vector
        return CoordinatePoint.from_point(normal_vec)
    
    def argument(self, reference=None):
        if reference is None:
            reference = self.midpoint()
        crosses = [reference.cross(p) for p in self._points]
        if self.closed:
            crosses.append(crosses[0])
        arg = 0
        for i in range(len(crosses) - 1):
            arg += reference.dot(crosses[i].cross(crosses[i + 1])) / (crosses[i].dot(crosses[i + 1]))
        return arg / reference.square()
    
    def orientation(self):
        arg = self.argument()
        if abs(arg) < np.pi:
            return 0
        elif arg > 0:
            return 1
        else:
            return -1
    
    def is_interior(self, point):
        argument = self.argument(reference=point)
        return abs(argument) > np.pi
    
class GeoPoint(GeoTag, CoordinatePoint):
    def __init__(self, name, long, lat, id=None, description=None):
        GeoTag.__init__(self, name, id, description)
        CoordinatePoint.__init__(self, long, lat)
    
    def __str__(self):
        return CoordinatePoint.__str__(self)
    
    def as_svg(self, projection=None, **kwargs):
        if projection is None:
            projection = lambda p: (p.longitude, p.latitude)
        lon, lat = projection(self)
        kwargs['cx'] = lon
        kwargs['cy'] = lat
        kwargs['r'] = kwargs.pop('radius', '3')
        return self.svg_element('circle', **kwargs)
    
    def as_kml(self, **kwargs):
        lon_precision = kwargs.pop('lon_precision', None)
        lat_precision = kwargs.pop('lat_precision', None)
        format_str = CoordinatePoint.kml_format(lon_precision, lat_precision)
        
        placemark = self.kml_element(**kwargs)
        point = ET.SubElement(placemark, 'Point')
        coordinates = ET.SubElement(point, 'coordinates')
        coordinates.text = format_str.format(self.longitude, self.latitude)
        return placemark
    
class GeoLine(GeoTag, CoordinateList):
    def __init__(self, name, id=None, description=None, points=None):
        GeoTag.__init__(self, name, id, description)
        CoordinateList.__init__(self, closed=False, points=points)
    
    def as_svg(self, projection=None, **kwargs):
        path_str = self.path_list(projection=projection)
        return self.svg_element('path', d=path_str, **kwargs)
    
    def as_kml(self, **kwargs):
        coord_str = self.kml_list()
        placemark = self.kml_element(**kwargs)
        linestring = ET.SubElement(placemark, 'LineString')
        coordinates = ET.SubElement(linestring, 'coordinates')
        coordinates.text = coord_str
        return placemark

class GeoPolygon(GeoLine):
    def __init__(self, name, points=None, id=None, description=None, inner=None):
        super().__init__(name, id=id, description=description, points=points)
        self.closed = True
        self._inner = self._check_orientation(inner)
        self._children = None
    
    @classmethod
    def copy(cls, polygon, name=None, id=None, description=None, inner=None):
        assert isinstance(polygon, CoordinateList)
        return cls(name or polygon.name, points=polygon.points, id=id, description=description, inner=inner)
    
    @property
    def inner(self):
        return self._inner
    
    @inner.setter
    def inner(self, inner):
        self._inner = self._check_orientation(inner)
    
    def _check_orientation(self, inner):
        if inner is None:
            return False
        orientation = self.orientation()
        if (inner and orientation < 0) or (not inner and orientation > 0):
            self.reverse()
        return bool(inner)
    
    def _auto_orientation(self):
        self._inner = self.orientation() > 0
    
    def kml_boundary(self, parent):
        boundary_tag = 'innerBoundaryIs' if self._inner else 'outerBoundaryIs'
        boundary = ET.SubElement(parent, boundary_tag)
        linear_ring = ET.SubElement(boundary, 'LinearRing')
        coordinates = ET.SubElement(linear_ring, 'coordinates')
        coordinates.text = coord_str
        return boundary
    
    def as_kml(self, **kwargs):
        coord_str = self.kml_list()
        placemark = self.kml_element(**kwargs)
        polygon = ET.SubElement(placemark, 'Polygon')
        self.kml_boundary(polygon)
        return placemark

class GeoComposite(GeoTag):
    def __init__(self, name, id=None, description=None):
        super().__init__(name, id, description)
        self._polygons = []
    
    def __len__(self):
        return len(self._polygons)
    
    def __bool__(self):
        return bool(self._polygons)
    
    def __getitem__(self, index):
        return self._polygons[index]
    
    def __iter__(self):
        return self._polygons
    
    def __append__(self, polygon):
        if len(polygon) == 0:
            raise ValueError("Cannot add an empty polygon")
        
        n = len(self._polygons)
        poly = GeoPolygon.copy(polygon, name=f'{self.name} {n+1}')
        
        first_point = poly[0]
        interior_to = [p for p in self._polygons if p.is_interior(first_point)]
        
        if len(interior_to) % 2 == 0:
            poly.inner = False
            poly._children = []
        else:
            smallest_polygon = min(interior_to, key=lambda p: p.normal().square())
            poly.inner = True
            smallest_polygon._children.append(poly)
        
        self._polygons.append(poly)
    
    def svg_list(self, projection=None):
        return "\n".join([p.as_svg(projection=projection) for p in self._polygons])
    
    def as_svg(self, projection=None, **kwargs):
        if len(self) == 0:
            raise ValueError("Cannot generate SVG representation with an empty collection")
        kwargs['fill-rule'] = 'evenodd'
        return self.svg_element('path', d=self.svg_list(projection=projection), **kwargs)
    
    def as_kml(self, **kwargs):
        if len(self) == 0:
            raise ValueError("Cannot generate KML representation with an empty collection")
        placemark = self.kml_element(**kwargs)
        multi_geometry = ET.SubElement(placemark, 'MultiGeometry')
        for polygon in self._polygons:
            if polygon.inner:
                continue
            polygon_tag = ET.SubElement(multi_geometry, 'Polygon')
            polygon.kml_boundary(polygon_tag)
            for child in polygon._children:
                child.kml_boundary(polygon_tag)
        return placemark
        
class GeoGroup(GeoTag):
    """Class representing a group of geographical elements."""
    
    def __init__(self, name, id=None, description=None):
        """Initialize a GeoGroup."""
        super().__init__(name, id, description)
        self._elements = []
    
    def __len__(self):
        """Get the number of elements in the group."""
        return len(self._elements)
    
    def __bool__(self):
        """Check if the group contains elements."""
        return bool(self._elements)
    
    def __getitem__(self, index):
        """Get an element from the group."""
        return self._elements[index]
    
    def __iter__(self):
        """Iterate over the elements in the group."""
        return iter(self._elements)
    
    def __append__(self, element):
        """Add a GeoTag element to the group."""
        if not isinstance(element, GeoTag):
            raise TypeError("Only instances of GeoTag can be added to a GeoGroup")
        self._elements.append(element)
    
    def remove_element(self, element):
        """Remove a GeoTag element from the group."""
        if element in self._elements:
            self._elements.remove(element)
    
    def as_svg(self, projection=None, **kwargs):
        """Generate SVG representation of the group."""
        svg_group = self.svg_element('g', **kwargs)
        for element in self._elements:
            svg_group.append(element.as_svg(projection=projection))
        return svg_group
    
    def as_kml(self, **kwargs):
        """Generate KML representation of the group."""
        folder = self.kml_element('Folder', **kwargs)
        for element in self._elements:
            folder.append(element.as_kml())
        return folder

class GeoDocument(GeoGroup):
    """Class representing a GeoDocument, which is the base group for geographical elements."""
    
    def __init__(self, name, id=None, description=None):
        """Initialize a GeoDocument."""
        super().__init__(name, id, description)
    
    def as_svg(self, projection=None, **kwargs):
        """Generate SVG representation of the document."""
        svg_document = self.svg_element('svg', **kwargs)
        for element in self._elements:
            svg_document.append(element.as_svg(projection=projection))
        return svg_document
    
    def as_kml(self, **kwargs):
        """Generate KML representation of the document."""
        kml_document = self.kml_element('Document', **kwargs)
        for element in self._elements:
            kml_document.append(element.as_kml())
        return kml_document

    @classmethod
    def from_klm(cls, url=None, file_obj=None, bytestring=None, element_tree=None):
        n = 0
        if url:
            kml_tree = KMLParser.fromfile(url)
            "TODO: check if it is valid KML"
            n+=1
        if file_obj:
            kml_tree = KMLParser.fromfile(file_obj)
            "TODO: check if it is valid KML"
            n+=1
        if bytestring:
            kml_tree = KMLParser.fromstring(bytestring)
            "TODO: check if it is valid KML"
            n+=1
        if element_tree:
            kml_tree = KMLParser(element_tree)
            "TODO: check if it is valid KML"
            n+=1
        if n == 0:
            raise ValueError("No valid KML source provided")
        if n > 1:
            raise ValueError("More than one valid KML source provided")
        return klm2geo(kml_tree)

def klm2geo(kml_tree):
    """Convert a KML tree to a GeoDocument."""
