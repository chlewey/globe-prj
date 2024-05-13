
from toolkit import cv
from GeoTag import *
from mysvgbin import SVGbin
import base64

class MapImage:
    _behaviors = ['nearest', 'bilinear', 'bicubic']

    def __init__(self, image_path, central_meridian=0.0, interpolation=cv.INTER_NEAREST):
        self._image = cv.imread(image_path)
        if self._image is None:
            raise FileNotFoundError(f"Unable to open image file: {image_path}")
        self._central_meridian = central_meridian
        self._interpolation = interpolation

    @property
    def image(self):
        return self._image
    
    @property
    def central_meridian(self):
        return self._central_meridian
    
    @property
    def interpolation(self):
        return self._behavior
    
    @central_meridian.setter
    def central_meridian(self, value):
        self._central_meridian = float(value)
        return value

    @interpolation.setter
    def interpolation(self, value):
        self._interpolation = value

    def coord_to_image(self, lon, lat):
        height, width = self.image.shape[:2]
        lon_normalized = ((lon - self.central_meridian + 180) / 360) % 1
        lat_normalized = (90 - lat) / 180
        x = lon_normalized * width
        y = lat_normalized * height
        return x, y

    def spatial_to_coord(self, point: np.ndarray):
        lon = np.degrees(np.arctan2(point[..., 0], point[..., 2]))
        lat = np.degrees(np.arctan2(point[..., 1], np.sqrt(point[..., 0]**2 + point[..., 2]**2)))
        return lon, lat
    
    def spatial_to_image(self, point: np.ndarray):
        lon = np.degrees(np.arctan2(point[..., 0], point[..., 2]))
        lat = np.degrees(np.arctan2(point[..., 1], np.sqrt(point[..., 0]**2 + point[..., 2]**2)))
        return self.coord_to_image(lon, lat)
    
    def get_value(self, point, interpolation=None):
        interpolation = interpolation or self._interpolation
        x, y = point[..., 0], point[..., 1]
        interp_value = cv.remap(self.image, np.array([x]), np.array([y]), interpolation)
        return interp_value

def split_text(text, chunk_size=80, first_chunk_size=None):
    if first_chunk_size is None:
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    return [text[:first_chunk_size]] + [text[i:i+chunk_size] for i in range(first_chunk_size, len(text), chunk_size)]

class Projection(collector, attributer):
    def __init__(self, name=None, **kwargs):
        name = name or self.__class__.__name__
        self._name = name
        self._outside = None
        attributes = { **self._default_params, **kwargs }
        collector.__init__(self, name)
        attributer.__init__(self, **attributes)
    
    _default_params = {
        'central_meridian': 0.0,
        'central_latitude': 0.0,
        'viewpoint_azimuth': 0.0,
        'map_size': (1440, 720),
        'window_size': None,
        'window_offset': (0,0)
    }
    def _valid_key(self, key):
        return key in self._default_params.keys()
    
    def __call__(self, point: CoordinatePoint):
        return self.coord_to_pixel(point)

    def coord_to_pixel(self, point: CoordinatePoint):
        x = 0.5 + (point.longitude - self.central_meridian)/360
        y = 0.5 - (point.latitude - self.central_latitude)/180
        x %= 1
        return self.map_size[0]*x, self.map_size[1]*y
    
    def pixel_to_coord(self, pixel):
        lon = (pixel[0]/self.map_size[0] - 0.5)*360 + self.central_meridian
        lat = (0.5 - pixel[1]/self.map_size[1])*180 + self.central_latitude
        return CoordinatePoint(lon, lat)
    
    def pixel_to_xyz(self, pixel, dtype=None):
        coord = self.pixel_to_coord(pixel)
        return tuple(coord) if dtype is None else coord._arg.astype(dtype)

    def area_map(self, dtype=np.float32):
        # Generate coordinate grid for all pixels in the area
        x_coords = np.arange(self.map_size[0])
        y_coords = np.arange(self.map_size[1])
        xx, yy = np.meshgrid(x_coords, y_coords, indexing='xy')

        # Convert area coordinates to XYZ coordinates
        coords = self.pixel_to_xyz((xx, yy), dtype=dtype)

        return coords
        
    def shift_offset(self, pixel):
        x = pixel[0] - self.window_offset[0]
        y = pixel[1] - self.window_offset[1]
        self._outside = x < 0 or x >= self.window_size[0] or y < 0 or y >= self.window_size[1]
        return x, y
    
    def unshift_offset(self, pixel):
        x = pixel[0] + self.window_offset[0]
        y = pixel[1] + self.window_offset[1]
        return x, y
    
    def coord_to_window(self, point: CoordinatePoint):
        return self.shift_offset(self.coord_to_pixel(point))
    
    def window_to_coord(self, pixel):
        return self.pixel_to_coord(self.unshift_offset(pixel))
    
    def window_to_xyz(self, pixel, dtype=None):
        coord = self.window_to_coord(pixel)
        return tuple(coord) if dtype is None else coord._arg.astype(dtype)
    
    def window_map(self, dtype=np.float32):
        # Generate coordinate grid for all pixels in the window
        x_coords = np.arange(self.window_size[0])
        y_coords = np.arange(self.window_size[1])
        xx, yy = np.meshgrid(x_coords, y_coords, indexing='xy')

        # Convert window coordinates to XYZ coordinates
        coords = self.window_to_xyz((xx, yy), dtype=dtype)

        return coords
    
    @property
    def outside(self):
        return self._outside

    @property
    def name(self):
        return self._name
    
    @property
    def central_point(self):
        return CoordinatePoint(self.central_meridian, self.central_latitude)
    
    @central_point.setter
    def central_point(self, value):
        assert len(value) >= 2
        self.central_meridian = float(value[0])
        self.central_latitude = float(value[1])
    
    @classmethod
    def get_projection(cls, name: str):
        if name in cls.keys():
            return cls[name].__class__
        id = cls.simplify_name(name)
        return cls[id] if id in cls.keys() else cls
        
    def set_central_point(self, point):
        if point is None:
            return False
        self.central_point = point
        return True
    
    def set_central_meridian(self, meridian):
        if meridian is None:
            return False
        self.central_meridian = meridian
        return True
    
    def set_central(self, value):
        if value is None:
            return False
        if isinstance(value, (int, float)):
            self.central_meridian = value
        else:
            self.central_point = value
        return True
    
    def set_viewpoint_azimuth(self, azimuth):
        if azimuth is None:
            return False
        self.viewpoint_azimuth = azimuth
        return True
    
    def set_map_size(self, size):
        if size is None:
            return False
        self.map_size = size
        return True
    
    def set_windwow_size(self, size):
        if size is None:
            return False
        self.window_size = size
        return True
    
    def set_window_offset(self, offset):
        if offset is None:
            return False
        self.window_offset = offset
        return True
    
    def mapless(self):
        return False
    
    def project_map(self, map_filename, interpolation=cv.INTER_NEAREST, over_map_area=False):
        map_image = MapImage(map_filename, interpolation=interpolation)
        coords = self.area_map() if over_map_area else self.window_map()
        image_coords = map_image.spatial_to_image(coords)
        return map_image.get_value(image_coords)
    
    def project_kml(self, kml_filename):
        geo_document = GeoDocument.from_klm(url=kml_filename)
        return geo_document
    
    def make_raster(self, raster_map, vector_map=None, filename=None):
        w, h = self.window_size
        x0, y0 = self.window_offset
        
        # Initialize output image
        if raster_map:
            if self.window_size == raster_map.shape[:2]:
                output_img = raster_map
            else:
                output_img = raster_map[y0:y0+h, x0:x0+w, :]
        else:
            output_img = np.zeros((h, w, 3), dtype=np.uint8)
        
        # Overlay vector map
        if vector_map:
            svg_tree = vector_map.as_svg(projection=self)
            svg_string = ET.tostring(svg_tree, encoding="unicode")
            png_bytes = cairosvg.svg2png(bytestring=svg_string)
            png_image = cv.imdecode(np.frombuffer(png_bytes, np.uint8), cv.IMREAD_COLOR)
            if self.window_size != png_image.shape[:2]:
                png_image = png_image[y0:y0+h, x0:x0+w, :]
            alpha = png_image[:, :, 3] / 255.0
            output_img = cv.addWeighted(output_img, 1 - alpha, png_image[:, :, :3], alpha, 0)
        
        # Save output_img to file if filename is provided
        if filename:
            cv.imwrite(filename, output_img)
        
        return output_img
    
    def make_vector(self, raster_map, vector_map, filename=None):
        if not vector_map:
            if self.window_size != self.map_size:
                viewbox = f"{self.window_offset[0]} {self.window_offset[1]} {self.window_size[0]} {self.window_size[1]}"
                vector_map = GeoDocument(self.name, width=self.window_size[0], height=self.window_size[1], viewBox=viewbox)
            else:
                vector_map = GeoDocument(self.name, width=self.map_size[0], height=self.map_size[1])
        svg_tree = vector_map.as_svg(projection=self)
        if raster_map:
            success, png_img = cv.imencode('.png', raster_map)
            shape = raster_map.shape
            if not success:
                raise ValueError('Error al codificar raster')
            base64_img = base64.b64encode(png_img).decode('utf-8')
            splitted_img = split_text(base64_img, 120, 80)
            svg_tree.insert(0, f'<image x="0" y="0" width="{shape[1]}" height="{shape[0]}" href="data:image/png;base64,{splitted_img}" />')
        if filename:
            svg_tree.write(filename)
        return ET.tostring(svg_tree, encoding="unicode")
