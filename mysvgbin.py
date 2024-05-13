
import xml.etree.ElementTree as ET
import cv2 as cv
import numpy as np
import io, sys, subprocess

try:
    import cairosvg
except (ImportError, OSError):
    pass

try:
    import svglib.svglib as svglib
except ImportError:
    pass

try:
    from PyQt5 import QtSvg, QtGui
except ImportError:
    pass

try:
    from PIL import Image
except ImportError:
    pass

class SVGbin:
    _inkscape_path = r"C:\Program Files\Inkscape\bin\inkscape.exe"
    _available = {}
    
    def __init__(self, bytestring=None, url=None, filehandle=None, etree=None):
        self._text = bytestring
        self._url = url
        self._filehandle = filehandle
        self._etree = etree
        self.ensure_text()
    
    @classmethod
    def from_url(cls, url):
        try:
            with open(url, 'rb') as f:
                text = f.read()
        except FileNotFoundError:
            raise ValueError('File not found.')
        return cls(url=url, bytestring=text)
    
    @classmethod
    def from_filehandle(cls, filehandle):
        text = filehandle.read()
        return cls(filehandle=filehandle, bytestring=text)
    
    @classmethod
    def from_etree(cls, etree):
        text = ET.tostring(etree)
        return cls(etree=etree, bytestring=text)
    
    @classmethod
    def from_text(cls, text):
        return cls(bytestring=text)
    
    @classmethod
    def set_inkscape_path(cls, path):
        cls._inkscape_path = path
    
    def ensure_text(self):
        if self._text:
            return self._text
        if self._url:
            try:
                with open(self._url, 'rb') as f:
                    self._text = f.read()
            except FileNotFoundError:
                raise ValueError('File not found.')
        elif self._filehandle:
            self._text = self._filehandle.read()
        elif self._etree:
            self._text = ET.tostring(self._etree)
        else:
            raise ValueError('No source specified.')
        return self._text
    
    def ensure_etree(self):
        if self._etree:
            return self._etree
        self._etree = ET.fromstring(self.ensure_text())
        return self._etree
    
    @property
    def text(self):
        return self.ensure_text()
    
    @property
    def url(self):
        return self._url
    
    @property
    def filehandle(self):
        return self._filehandle
    
    @property
    def etree(self):
        return self.ensure_etree()
    
    def set_inkscape_path(cls, path):
        cls._inkscape_path = path
    
    def image_by_cairo(self):
        try:
            png_bytes = cairosvg.svg2png(bytestring=self.text)
        except NameError:
            raise ValueError('CairoSVG not installed.')
        return cv.imdecode(np.frombuffer(png_bytes, np.uint8), cv.IMREAD_UNCHANGED)
    
    def image_by_svglib(self):
        try:
            drawing = svglib.svg2rlg(ET.fromstring(self.text))
        except NameError:
            raise ValueError('svglib not installed.')
        try:
            drawing_image = Image.new("RGBA", (drawing.width, drawing.height))
            drawing_image.paste(drawing, (0, 0))
        except NameError:
            raise ValueError('PIL not installed.')
        return np.array(drawing_image)
    
    def image_by_PIL(self):
        try:
            drawing = Image.open(io.BytesIO(self.text))
        except NameError:
            raise ValueError('PIL not installed.')
        return np.array(drawing)
    
    def image_by_inkscape(self):
        with open('temp.svg', 'wb') as f:
            f.write(self.text.encode('utf-8'))
        try:
            subprocess.run([self._inkscape_path, '--export-type=png', '--export-filename=temp.png', 'temp.svg'], check=True)
        except subprocess.CalledProcessError:
            raise ValueError('Inkscape not installed.')
        return cv.imread('temp.png', cv.IMREAD_UNCHANGED)
    
    def image_by_Qt(self):
        try:
            svg_renderer = QtSvg.QSvgRenderer(ET.tostring(self.etree))
            drawing = QtGui.QImage(self.etree.attrib['width'], self.etree.attrib['height'], QtGui.QImage.Format_ARGB32)
            painter = QtGui.QPainter(drawing)
        except NameError:
            raise ValueError('Qt not installed.')
        svg_renderer.render(painter)
        painter.end()
        return np.array(drawing)
    
    @classmethod
    def check_cairo(cls):
        cls._available['CairoSVG'] = 'cairosvg' in sys.modules
        return cls._available['CairoSVG']
    
    @classmethod
    def check_svglib(cls):
        cls._available['svglib'] = 'svglib' in sys.modules or 'svglib.svglib' in sys.modules
        return cls._available['svglib']
    
    @classmethod
    def check_PIL(cls):
        cls._available['PIL'] = 'PIL' in sys.modules
        return cls._available['PIL']
    
    @classmethod
    def check_inkscape(cls):
        try:
            subprocess.run([cls._inkscape_path, '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cls._available['Inkscape'] = True
        except subprocess.CalledProcessError:
            cls._available['Inkscape'] = False
        return cls._available['Inkscape']
    
    @classmethod
    def check_Qt(cls):
        cls._available['Qt'] = 'QtSvg' in sys.modules
        return cls._available['Qt']
    
    @classmethod
    def check_available(cls):
        cls.check_inkscape()
        cls.check_cairo()
        cls.check_svglib()
        cls.check_PIL()
        cls.check_Qt()
        return cls._available
    
    def __call__(self, preferred=None):
        available = [key for key in self._available if self._available[key]]
        if not available:
            raise ValueError('No image library available.')
        library = preferred if preferred in available else available[0]
        if library == 'CairoSVG':
            return self.image_by_cairo()
        elif library == 'svglib':
            return self.image_by_svglib()
        elif library == 'PIL':
            return self.image_by_PIL()
        elif library == 'Inkscape':
            return self.image_by_inkscape()
        elif library == 'Qt':
            return self.image_by_Qt()
        else:
            raise ValueError(f'Unknown image library: {library}.')


if __name__ == '__main__':
    print(SVGbin.check_available())
    
    svg_text = '<svg width="5" height="5"><rect x="1" y="1" width="3" height="3" fill="red"/><circle cx="2.5" cy="2.5" r="2.5" fill="blue" opacity="0.5"/></svg>'
    image = SVGbin(svg_text)()
    print(image)
