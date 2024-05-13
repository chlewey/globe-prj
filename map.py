
import programEngine as PE
from MapProjection import *
import re, os

class MapProgram(PE.Program):
    def __init__(self, *args, **kwargs):
        super().__init__('MapProgram')
        self.cmd.projection = self.cmd.argument('map projection to use')
        self.cmd.file = self.cmd.group()
        self.cmd.file.map = self.cmd.store_arg('[m]ap-file', 'input raster map file', type=str)
        self.cmd.file.kml = self.cmd.store_arg('[k]ml-file', 'input kml file', type=str)
        self.cmd.file.output = self.cmd.store_arg('[o]utput', 'output raster map file', type=str)
        self.cmd.file.svg = self.cmd.store_arg('[s]vg-file', 'output svg file', type=str)
        self.cmd.file.groups = self.cmd.store_arg('[g]roups', 'output groups file', type=str)
        self.cmd.parameters = self.cmd.group()
        self.cmd.parameters.central = self.cmd.store_arg('[c]entral-meridian', 'central meridian', type=float)
        self.cmd.parameters.point = self.cmd.store_arg('central-[p]oint', 'central point', type=PE.arg_coord)
        self.cmd.parameters.azimuth = self.cmd.store_arg('[a]zimuth', 'viewpoint azimuth', type=float)
        self.cmd.formating = self.cmd.group()
        self.cmd.formating.size = self.cmd.store_arg('si[z]e', 'output map size', type=PE.arg_size)
        self.cmd.formating.window = self.cmd.store_arg('[w]indow', 'output image window size', type=PE.arg_size)
        self.cmd.formating.shift = self.cmd.store_arg('sh[i]ft', 'output image shift', type=PE.arg_size)
        self.cmd.control = self.cmd.group()
        self.cmd.control.verbosity = self.cmd.count_arg('[v]erbose', 'increases verbosity level', auto_exclude=True)
        self.cmd.control.verbosity+= self.cmd.store_arg('[q]uiet', 'quiet mode', const=-1)
        self.cmd.control.debug = self.cmd.flag('debug', 'muestra información de depuración', short=None)
        self.cmd.control.set_version('1.0')
    
    def findfile(self, name, type='auto'):
        name = name or ''
        answer = None
        if re.match(r'^\w+$', name):
            if type in ('auto', 'map') or type=='map':
                with open('objects/maps.csv') as indexfile:
                    for line in indexfile:
                        if name == line.split(',')[0]:
                            answer =  line.split(',')[1]
                            break
            elif type in ('auto', 'kml') or type=='kml':
                with open('objects/kmls.csv') as indexfile:
                    for line in indexfile:
                        if name == line.split(',')[0]:
                            answer =  line.split(',')[1]
                            break
            if answer is None:
                if type == 'auto':
                    for ext in ('png','PNG','jpg', 'JPG', 'jpeg', 'JPEG', 'kml', 'kmz'):
                        if os.path.isfile(name + '.' + ext):
                            return name + '.' + ext
                elif type == 'map':
                    for ext in ('png','PNG','jpg', 'JPG', 'jpeg', 'JPEG'):
                        if os.path.isfile(name + '.' + ext):
                            return name + '.' + ext
                elif type == 'kml':
                    for ext in ('kml', 'kmz'):
                        if os.path.isfile(name + '.' + ext):
                            return name + '.' + ext
        else:
            answer = name
        if not answer:
            return None
        if not os.path.isfile(answer):
            raise FileNotFoundError(f'No se encontró el archivo: {answer}')
        return answer
    
    def __call__(self, *args, **kwargs):
        super().__call__(*args, **kwargs)
        
        map_file = self.findfile(self.arg.map, 'map')
        kml_file = self.findfile(self.arg.kml, 'kml')
        
        projection = Projection[self.arg.projection]
        
        if map_file is None and kml_file is None and not projection.mapless():
            raise ValueError('No hay archivo de mapas o KML')
        
        projection.set_central(self.arg.point or self.arg.central)
        projection.set_viewpoint_azimuth(self.arg.azimuth)
        projection.set_map_size(self.arg.size)
        projection.set_window_size(self.arg.window)
        projection.set_window_offset(self.arg.shift)
        
        raster = projection.project_map(map_file)
        vector = projection.project_kml(kml_file)
        
        if self.arg.output is None and self.arg.svg is None and not projection.mapless():
            raise ValueError('No hay archivo de salida')
        
        if self.arg.output is not None:
            projection.make_raster(raster, vector, self.arg.output)
        
        if self.arg.svg is not None:
            projection.make_vector(raster, vector, self.arg.svg)
        
        return self

if __name__ == '__main__':
    from sys import argv
    main = MapProgram(*argv)
    main()