import xml.etree.ElementTree as ET

class SVGParser(ET.ElementTree):
    def __init__(self, filename=None, svg_text=None, width=None, height=None, **kwargs):
        if filename:
            super().__init__()
            self.parse(filename)
        elif svg_text:
            super().__init__(ET.fromstring(svg_text))
        else:
            root = ET.Element('svg')
            root.set('xmlns', 'http://www.w3.org/2000/svg')
            root.set('width', str(width) or '100%')
            root.set('height', str(height) or '100%')
            for option in ['id', 'viewBox']:
                if option in kwargs:
                    root.set(option, kwargs[option])
            if 'offset' in kwargs or 'scale' in kwargs) and ('viewBox' not in kwargs):
                os_x, os_y = kwargs.get('offset', (0, 0))
                scale = kwargs.get('scale', 1)
                root.set('viewBox', f'{os_x} {os_y} {width*scale} {height*scale}')
            super().__init__(root)

    @classmethod
    def fromstring(cls, svg_text):
        return cls(svg_text=svg_text)
    
    @classmethod
    def fromfile(cls, filename):
        return cls(filename=filename)
    
    @classmethod
    def empty(class, width, height, **kwargs):
        return cls(width=width, height=height, **kwargs)
    
    def parse(self, file_path):
        super().parse(file_path)
        # Custom parsing logic for SVG
        # For example, extracting paths, shapes, etc.
        for element in self.getroot().iter():
            # Example parsing logic
            if 'id' in element.attrib:
                print("SVG element with id:", element.attrib['id'])
    
    def add_element(self, tag, **kwargs):
        parent = kwargs.pop('parent', self.getroot())
        text = kwargs.pop('text', None)
        element = ET.Element(tag, **kwargs)
        if text:
            element.text = text
        parent.append(element)
        return element

    def add_group(self, **kwargs):
        return self.add_element('g', **kwargs)

    def add_path(self, path, **kwargs):
        kwargs[d] = path
        return self.add_element('path', **kwargs)

class KMLParser(ET.ElementTree):
    def __init__(self, filename=None, kml_text=None, **kwargs):
        if filename:
            super().__init__()
            self.parse(filename)
        elif kml_text:
            super().__init__(ET.fromstring(kml_text))
        else:
            root = ET.Element('kml')
            root.set('xmlns', 'http://www.opengis.net/kml/2.2')
            super().__init__(root)

    @classmethod
    def fromstring(cls, kml_text):
        return cls(kml_text=kml_text)
    
    @classmethod
    def fromfile(cls, filename):
        return cls(filename=filename)
    
    @classmethod
    def empty(cls):
        return cls()

    def parse(self, file_path):
        super().parse(file_path)
        # Custom parsing logic for KML
        # For example, extracting coordinates, placemarks, etc.
        for element in self.getroot().iter():
            # Example parsing logic
            if 'name' in element.attrib:
                print("KML element with name:", element.attrib['name'])


if __name__ == "__main__":
    # Example usage
    svg_file = "example.svg"
    svg_parser = SVGParser(svg_file)

    kml_file = "example.kml"
    kml_parser = KMLParser(kml_file)