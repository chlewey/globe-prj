
import argparse, sys, re

P_VERBOSITY_LEVEL = 1
P_VERBOSITY_MULTILEVEL = 2
P_VERBOSITY_SIMPLE = 3
P_VERBOSITY_TRIVIAL = 4
P_VERBOSITY_QUIETER = 5

def ensure_prefix(s, prefix, clean='_'):
    if not s or str(s).startswith(prefix):
        return s
    return prefix + str(s).strip(clean)

def initial(s, clean='_-'):
    return str(s).strip(clean)[0]

def arg_coord(s):
    splitted = s.split(',')
    if len(splitted)<2:
        return float(s), 0.0
    return float(splitted[0]), float(splitted[1])

def arg_frac(s):
    splitted = s.split('/')
    if len(splitted)<2:
        return int(s), 1
    return int(splitted[0]), int(splitted[1])

def arg_size(s):
    splitted = s.split(',')
    if len(splitted)<2:
        return int(s), int(s)
    return int(splitted[0]), int(splitted[1])

class Program:
    class Arguments(argparse.Namespace):
        pass

    class ParserItem():
        def __init__(self, *args, **kwargs):
            self._args = args
            self._kwargs = kwargs
            self._object = None
            self._name = None

        def _decode_args(self, name):
            long_arg, short_arg = None, None
            num_args = len(self._args)

            if num_args and ' ' in self._args[-1]:
                self._kwargs['help'] = self._args[-1]
                num_args -= 1

            if self._kwargs.pop('positional', False):
                self._args = (name,)
                self._kwargs.pop('dest', None)
                return self._args, self._kwargs

            if num_args == 1:
                first_arg = str(self._args[0])
                if '[' in first_arg:
                    parts = re.split('\[|\]', self._args[0])
                    long_arg, short_arg = ''.join(parts), parts[1]
                elif first_arg.startswith('--'):
                    long_arg, short_arg = first_arg, None
                elif first_arg.startswith('-'):
                    long_arg, short_arg = None, first_arg
                else:
                    long_arg, short_arg = first_arg, initial(first_arg)
            elif num_args >= 2:
                first_arg, second_arg = str(self._args[0]), str(self._args[1])
                if len(first_arg.strip('_-')) == 1:
                    long_arg, short_arg = second_arg, initial(first_arg)
                else:
                    long_arg, short_arg = first_arg, initial(second_arg)
            else:
                long_arg, short_arg = name, initial(name)

            long_arg = ensure_prefix(self._kwargs.pop('long', long_arg).lower(), '--')
            short_arg = ensure_prefix(self._kwargs.pop('short', short_arg), '-')
            self._args = (long_arg,) if not short_arg else (short_arg,) if not long_arg else (short_arg, long_arg)
            self._kwargs['dest'] = name
            return self._args, self._kwargs
            
        def assign_to(self, parser, name):
            assert isinstance(parser, (Program.Parser, argparse.ArgumentParser, argparse._ArgumentGroup))
            self._decode_args(name)
            if self._kwargs.pop('auto_exclude', False):
                self._object = parser.add_mutually_exclusive_group()
            elif self._kwargs.pop('auto_group', False):
                description = self._kwargs.pop('description', None)
                self._object = parser.add_argument_group(name, description)
            sub = self._object if isinstance(self._object, argparse._ArgumentGroup) else parser
            argument = sub.add_argument(*self._args, **self._kwargs)
            if self._object is None:
                self._object = argument
            self._name = name
            return self

        def __iadd__(self, parser_item):
            assert isinstance(self._object, argparse._ArgumentGroup)
            assert isinstance(parser_item, Program.ParserItem)
            parser_item.assign_to(self._object, self._name)
            return self

        def __str__(self) -> str:
            args_str = ", ".join(self._args)
            kwargs_str = ", ".join([f"{k}={repr(v)}" for k,v in self._kwargs.items()])
            return f'<ParseItem {type(self._object)} | {args_str}, {kwargs_str}>'

    class Parser(argparse.ArgumentParser):
        def __init__(self, parent, *args, **kwargs):
            assert isinstance(parent, (Program, Program.Parser)), f'parent must be an instance of Program, current is {type(parent)}'
            self._parent = parent
            self._items = {}
            super().__init__(*args, **kwargs)

        def __setattr__(self, name, value):
            if isinstance(value, Program.ParserItem):
                if name not in self._items:
                    self._items[name] = value.assign_to(self, name)
                elif not isinstance(self._items[name]._object, argparse._ArgumentGroup):
                    raise ValueError(f'parser item {name} already exist and is no group')
                return self._items[name]
            super().__setattr__(name, value)

        def __getattr__(self, name):
            if name in self._items:
                return self._items[name]
            raise AttributeError(name)

        def ensure_group(self, title, mutually_exclusive=False, description=None):
            if title not in self._groups:
                self._groups[title] = Program.ParserGroup(mutually_exclusive, description).assign_to(self, title)
            return self._groups[title]
        
        def set_verbosity(self, verbosity_type, **kwargs):
            verbosity_group = kwargs.pop('verbosity_group', 'verbosity')

            verbose_var = kwargs.pop('verbose', 'verbose')
            verbose_long = ensure_prefix(kwargs.pop('verbose_long', verbose_var), '--')
            verbose_short = ensure_prefix(kwargs.pop('verbose_short', initial(verbose_var)), '-')
            verbose_args = [verbose_short] if not verbose_long else [verbose_long] if not verbose_short else [verbose_short, verbose_long]
            self._parent._param_aliases['verbose'] = verbose_var

            quiet_var = kwargs.pop('quiet', 'quiet')
            quiet_long = ensure_prefix(kwargs.pop('quiet_long', quiet_var), '--')
            quiet_short = ensure_prefix(kwargs.pop('quiet_short', initial(quiet_var)), '-')
            quiet_args = [quiet_short] if not quiet_long else [quiet_long] if not quiet_short else [quiet_short, quiet_long]
            self._parent._param_aliases['quiet'] = quiet_var
            
            if verbosity_type in {P_VERBOSITY_LEVEL, P_VERBOSITY_MULTILEVEL, P_VERBOSITY_SIMPLE}:
                subparser = self.ensure_group(verbosity_group, True)
            elif verbosity_type in {P_VERBOSITY_TRIVIAL, P_VERBOSITY_QUIETER}:
                subparser = self
            else:
                raise ValueError
            
            if verbosity_type in {P_VERBOSITY_LEVEL, P_VERBOSITY_MULTILEVEL}:
                subparser.add_argument(*verbose_args, dest=verbose_var, action='count', default=0, help='increase verbosity')
            elif verbosity_type in {P_VERBOSITY_SIMPLE, P_VERBOSITY_TRIVIAL}:
                subparser.add_argument(*verbose_args, dest=verbose_var, action='store_true', default=False, help='verbose mode')

            if verbosity_type in {P_VERBOSITY_MULTILEVEL}:
                subparser.add_argument(*quiet_args, dest=quiet_var, action='count', default=0, help='decrease verbosity')
            elif verbosity_type in {P_VERBOSITY_LEVEL, P_VERBOSITY_SIMPLE, P_VERBOSITY_QUIETER}:
                subparser.add_argument(*quiet_args, dest=quiet_var, action='store_true', default=False, help='quiet mode')
            
            return self
        
        def set_mode_flag(self, flag, **kwargs):
            group_name = kwargs.pop('group_name', None)
            group_description = kwargs.pop('group_description', None)
            subparser = self.ensure_group(group_name, description=group_description) if group_name else self

            flag_var = kwargs.pop('dest', flag)
            flag_long = ensure_prefix(kwargs.pop('long', flag_var), '--')
            flag_short = ensure_prefix(kwargs.pop('short', initial(flag_var)), '-')
            flag_args = [flag_short] if not flag_long else [flag_long] if not flag_short else [flag_short, flag_long]
            self._parent._param_aliases[flag] = flag_var

            subparser.add_argument(*flag_args, dest=flag_var, action='store_true', default=False, help=f'{flag} mode')
            return self
        
        def set_version(self, version, *args, **kwargs):
            word = args[0] if args else 'version'
            sub = self._object if hasattr(self, '_object') else self
            kwargs['action'] = 'version'
            kwargs['version'] = '%(prog)s '+version
            long_arg = ensure_prefix(kwargs.pop('long', word), '--')
            short_arg = ensure_prefix(kwargs.pop('short', None), '-')
            args = [short_arg] if not long_arg else [long_arg] if not short_arg else [short_arg, long_arg]
            sub.add_argument(*args, **kwargs)
            return self

        def argument(self, *args, optional=False, **kwargs):
            kwargs['positional'] = True
            if kwargs.pop('optional', optional):
                kwargs['nargs'] = '?'
            return Program.ParserItem(*args, **kwargs)

        def store_arg(self, *args, **kwargs):
            if 'const' in kwargs:
                const_val = kwargs.pop('const')
                if const_val is True:
                    kwargs['action'] = 'store_true'
                elif const_val is False:
                    kwargs['action'] = 'store_false'
                else:
                    kwargs['action'] = 'store_const'
                    kwargs['const'] = const_val
            else:
                kwargs['action'] = 'store'
            return Program.ParserItem(*args, **kwargs)
        
        def append_arg(self, *args, **kwargs):
            kwargs['action'] = 'append' if 'const' not in kwargs else 'append_const'
            return Program.ParserItem(*args, **kwargs)
        
        def count_arg(self, *args, **kwargs):
            kwargs['action'] = 'count'
            if 'default' not in kwargs:
                kwargs['default'] = 0
            return Program.ParserItem(*args, **kwargs)
        
        def flag(self, *args, **kwargs):
            kwargs['action'] = 'store_true'
            return Program.ParserItem(*args, **kwargs)
        
        def group(self, *args, **kwargs):
            return Program.ParserGroup(*args, **kwargs)

    class ParserGroup(ParserItem, Parser):
        def __init__(self, mutually_exclusive=False, description=None, *args, **kwargs):
            self._mutually_exclusive = mutually_exclusive
            self._description = description
            Program.ParserItem.__init__(self, *args, **kwargs)

        def assign_to(self, parser, title):
            Program.Parser.__init__(self, parser, *self._args, **self._kwargs)
            assert isinstance(parser, (Program.Parser, argparse.ArgumentParser, argparse._ArgumentGroup))
            if self._mutually_exclusive:
                self._object = parser.add_mutually_exclusive_group()
            else:
                self._object = parser.add_argument_group(title, self._description)
            return self

        def __setattr__(self, name, value):
            if isinstance(value, Program.ParserItem):
                if name not in self._items:
                    self._items[name] = value.assign_to(self._object, name)
                elif not isinstance(self._items[name]._object, argparse._ArgumentGroup):
                    raise ValueError(f'parser item {name} already exist and is no group')
                return self._items[name]
            return super().__setattr__(name, value)

    def __init__(self, title):
        self._title = title
        self._groups = {}
        self._parser = Program.Parser(self, title)
        self._params = Program.Arguments()
        self._parsed = False
        self._param_aliases = {}

    def _set_parametes(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self._params, key, value)

    @property
    def cmd(self):
        return self._parser
    
    @property
    def arg(self):
        return self._params

    def _param(self, param_name, default=None):
        if param_name in self._param_aliases:
            return getattr(self._params, self._param_aliases[param_name])
        if param_name in self._params.__dict__:
            return getattr(self._params, param_name)
        return default
    
    def _param_set(self, param_name, value, force=False):
        if param_name in self._param_aliases:
            setattr(self._params, self._param_aliases[param_name], value)
        if param_name in self._params.__dict__ or force:
            setattr(self._params, param_name, value)
    
    def _has_param(self, param_name):
        return param_name in self._param_aliases or param_name in self._params.__dict__

    def use_group(self, group, group_type):
        if not group:
            return self._parser
        if group not in self._groups:
            if group_type == 0:
                self._groups[group] = self._parser.add_argument_group(group)
            else:
                self._groups[group] = self._parser.add_mutually_exclusive_group()
        return self._groups[group]

    def add_argument(self, *args, **kwargs):
        group_name = kwargs.pop('group', '')
        if '!' in group_name:
            group_name = group_name.strip('!')
            group_type = 1
        else:
            group_type = 0
        sub = self.use_group(group_name, group_type)
        sub.add_argument(*args, **kwargs)

    def __str__(self):
        params = []
        for key, value in self._params.__dict__.items():
            params.append(f'{key}={value.__repr__()}')
        return self._title + '(' + ', '.join(params) + ')'

    def __repr__(self):
        return '<MiddeloProgram ' + self.__str__() + '>'
    
    @property
    def title(self):
        return self._title
    
    @property
    def verbosity(self):
        if self._has_param('verbosity'):
            return int(self._param('verbosity', 0))
        return int(self._param('verbose', 0)) - int(self._param('quiet', 0))
    
    @verbosity.setter
    def verbosity(self, level):
        if self._has_param('verbosity'):
            self._param_set('verbosity', level)
        else:
            self._param_set('verbose', level > 0 if isinstance(self._param('verbose'), bool) else max(level, 0))
            self._param_set('quiet', level < 0 if isinstance(self._param('quiet'), bool) else max(-level, 0))

    def __getattr__(self, name):
        if self._has_param(name):
            return self._param(name)
        raise AttributeError(name)

    def bool(self, attribute, default=False):
        return bool(self._param(attribute)) if self._has_param(attribute) else default

    def print(self, *args, **kwargs):
        if self.verbosity >= 0:
            print(*args, **kwargs)

    def message(self, *args, **kwargs):
        if self.verbosity >= 1:
            print(*args, **kwargs)
    
    def note(self, *args, **kwargs):
        if self.verbosity >= 2:
            print(*args, **kwargs)
    
    def noticule(self, *args, **kwargs):
        if self.verbosity >= 3:
            print(*args, **kwargs)

    def debug(self, *args, **kwargs):
        if self.bool('debug'):
            print('Debug:', *args, **kwargs)
        elif self.verbosity >= 3:
            print(*args, **kwargs)

    def obscure(self, *args, **kwargs):
        if self.verbosity >= 4:
            print(*args, **kwargs)

    def fatal(self, *args, **kwargs):
        kwargs['file'] = sys.stderr
        print('Fatal error:', *args, **kwargs)
        exit(kwargs.get('errlvl', 1))

    def error(self, *args, **kwargs):
        kwargs['file'] = sys.stderr
        if self.verbosity >= 0 or self.bool('debug'):
            print('Error:', *args, **kwargs)

    def warning(self, *args, **kwargs):
        kwargs['file'] = sys.stderr
        if self.verbosity >= 1 or self.bool('debug'):
            print('Warning:', *args, **kwargs)

    def new_argument(self, *args, **kwargs):
        return Program.ParserArgument(*args, **kwargs)
    

    def __call__(self, **kwargs):
        args = kwargs.pop('args', None)
        if not self._parsed:
            self._parser.parse_args(args, namespace=self._params)
            self._parsed = True
        else:
            self._set_parametes(**kwargs)
        return self

if __name__ == "__main__":
    class Test(Program):
        def __call__(self, **kwargs):
            super().__call__(**kwargs)
            self.debug(repr(self))
            self.print(f'Este es un mensaje importante que sólo se omitirá en modo silencioso. El nivel de verbosidad es de {self.verbosity}.')
            self.message('Este es un mensaje corriente que sólo se mostrará en algún modo verboso (nivel>0).')
            self.note('Esta es una anotación que sólo se mostrará si el nivel de verbosidad es de 2 o más.')
            self.debug('Este es un mensaje de depuración que solo se mostrará si el nivel de verbosidad es de 3 o más.')
            self.obscure('Este es un mensaje oculto que solo se mostrará si el nivel de verbosidad es de 4 o más.')

            self.error('Este es un mensaje de error.')
            self.warning('Este es un mensaje de advertencia.')
            #self.fatal('Este es un mensaje de error fatal.')

            if self.verbosity < 0:
                self.debug(self.verbosity)
            return self

    main = Test('MiddeloTest')
        
    main.cmd.input_file  = main.cmd.argument('name of input file')
    main.cmd.output_file = main.cmd.argument('name of output file', optional=True)
    main.cmd.verbosity   = main.cmd.count_arg('[v]erbose', auto_exclude=True, help='increase verbosity level')
    main.cmd.verbosity  += main.cmd.store_arg('[q]uiet', const=-1, help='quiet mode')
    main.cmd.verbosity  += main.cmd.store_arg('verbose_[l]evel', type=int, help='set verbosity level')
    main.cmd.debugging   = main.cmd.group()
    main.cmd.debugging.debug = main.cmd.flag('debug', short=None, help='debug mode')
    main.cmd.debugging.set_version('1.0')

    main()

    #print(main.__dict__)