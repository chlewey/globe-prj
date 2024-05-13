
import numpy as np
import cv2 as cv
import re

class ClassPropertyDescriptor(object):
    """
    Descriptor for defining class properties with both getter and setter methods.
    """
    
    def __init__(self, fget, fset=None):
        """
        Initialize the ClassPropertyDescriptor.
        
        Args:
            fget (callable): The getter method.
            fset (callable, optional): The setter method. Defaults to None.
        """
        self.fget = fget
        self.fset = fset
    
    def __get__(self, obj, klass=None):
        """
        Get the value of the property.
        
        Args:
            obj: The instance object.
            klass: The class object. Defaults to None.
        
        Returns:
            Any: The value of the property.
        """
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()
    
    def __set__(self, obj, value):
        """
        Set the value of the property.
        
        Args:
            obj: The instance object.
            value: The value to set.
        
        Returns:
            Any: The result of setting the value.
        """
        if not self.fset:
            raise AttributeError("can't set attribute")
        type_ = type(obj)
        return self.fset.__get__(obj, type_)(value)
    
    def setter(self, func):
        """
        Set the setter method of the property.
        
        Args:
            func (callable): The setter method.
        
        Returns:
            ClassPropertyDescriptor: The ClassPropertyDescriptor instance.
        """
        if not isinstance(func, (classmethod, staticmethod)):
            func = classmethod(func)
        self.fset = func
        return self

def classproperty(func):
    """
    Decorator for defining class properties.
    
    Args:
        func (callable): The method to decorate.
    
    Returns:
        ClassPropertyDescriptor: The descriptor for the class property.
    """
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)
    
    return ClassPropertyDescriptor(func)

class _itemized(type):
    """
    Metaclass for creating a class with dictionary-like behavior.
    """
    
    def __getitem__(cls, id):
        """
        Get an item by its ID.
        
        Args:
            id: The ID of the item.
        
        Returns:
            Any: The item with the specified ID.
        """
        return cls.get(id)
    
    def __setitem__(cls, id, value):
        """
        Set an item with the specified ID.
        
        Args:
            id: The ID of the item.
            value: The value to set for the item.
        """
        cls.set(id, value)

class collector(object, metaclass=_itemized):
    """
    Class for managing instances in a dictionary-like manner.
    """
    
    _items = {}
    
    def __init__(self, id, what=None):
        """
        Initialize a collector instance.
        
        Args:
            id: The ID of the instance.
        """
        id = self._set_id(id, what)
        super().__init__()
    
    def _set_id(self, id, what=None):
        """
        Set the ID for the instance.
        
        Args:
            id: The proposed ID.
        
        Returns:
            str: The finalized ID.
        """
        items = self.__class__._items
        if id in items:
            n = 1
            while f'{id}-{n:02d}' in items:
                n += 1
            id = f'{id}-{n:02d}'
        items[id] = what or self
        return id
    
    @classmethod
    def simplify_name(name):
        """
        Simplify a name by converting it to lowercase and replacing spaces with hyphens.
        
        Args:
            name (str): The name to simplify.
        
        Returns:
            str: The simplified name.
        """
        return name.lower().replace(' ', '-')
    
    @classmethod
    def items(cls):
        """
        Get all items in the collector.
        
        Returns:
            dict: A dictionary containing all items.
        """
        return cls._items
    
    @classmethod
    def get(cls, id):
        """
        Get an item by its ID.
        
        Args:
            id: The ID of the item.
        
        Returns:
            Any: The item with the specified ID.
        """
        return cls._items[id]
    
    @classmethod
    def has(cls, id):
        """
        Check if an item with the specified ID exists.
        
        Args:
            id: The ID to check.
        
        Returns:
            bool: True if the item exists, False otherwise.
        """
        return id in cls._items
    
    @classmethod
    def set(cls, id, value):
        """
        Set an item with the specified ID.
        
        Args:
            id: The ID of the item.
            value: The value to set for the item.
        
        Raises:
            ValueError: If the value is not an instance of the collector class.
        """
        if isinstance(value, cls):
            cls._items[id] = value
        else:
            raise ValueError(f'{value} is not an instance of {cls}')
    
    @classmethod
    def keys(cls):
        """
        Get the keys of all items in the collector.
        
        Returns:
            list: A list of keys.
        """
        return cls._items.keys()
    
    @classmethod
    def values(cls):
        """
        Get the values of all items in the collector.
        
        Returns:
            list: A list of values.
        """
        return cls._items.values()
    
    @classproperty
    def dict(cls):
        """
        Get the dictionary containing all items in the collector.
        
        Returns:
            dict: A dictionary of items.
        """
        return cls._items
    
    
class attributer(object):
    def __init__(self, **kwargs):
        self._attributes = { key:value for key, value in kwargs.items() if key[0] != '_' }
        super().__init__()

    def _valid_key(self, key):
        return not key.startswith('_')

    def __getattr__(self, name):
        if name.startswith('_') or name in self.__dict__:
            return super().__getattribute__(name)
        if name in self._attributes:
            return self._attributes[name]
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        
    def __setattr__(self, name: str, value) -> None:
        if name.startswith('_') or name in self.__dict__:
            super().__setattr__(name, value)
        if name in self._attributes.keys() or self._valid_key(name):
            self._attributes[name] = value
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object can't assign attribute '{name}'")
