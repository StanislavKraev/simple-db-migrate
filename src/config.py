import codecs
import os
import sys
import re

class Config(object):
    
    DB_VERSION_TABLE = "__db_version__"
    
    def __init__(self):
        self._config = {}
        
    def __repr__(self):
        return str(self._config)

    def get(self, config_key):
        try:
            return self._config[config_key]
        except KeyError:
            raise Exception("invalid configuration key ('%s')" % config_key)
            
    def put(self, config_key, config_value):
        if config_key in self._config:
            raise Exception("the configuration key '%s' already exists and you cannot override any configuration" % config_key)
        self._config[config_key] = config_value
        
    def _parse_migrations_dir(self, dirs, config_dir=''):
        abs_dirs = []
        for dir in dirs.split(':'):
            if config_dir == '':
                abs_dirs.append(os.path.abspath(dir))
            else:
                abs_dirs.append(os.path.abspath('%s/%s' % (config_dir, dir)))
        return abs_dirs
    
class FileConfig(Config):
    
    class SettingsFile(object):
        @staticmethod
        def get_file_imports(filename):
            imports = []
            try:
                f = open(filename)
                for line in f:
                    line = line.rstrip()
                    if line.startswith('import') or line.startswith('from'):
                        imports.append(line)
            finally:
                f.close()
            return imports
        
        @staticmethod
        def exec_import(import_line, global_variables, local_variables):
            if import_line.startswith('import'):
                modules = import_line.lstrip('import').split(',')
                for module in modules:
                    __import__(module.strip(), global_variables, local_variables, [], -1)
            else:
                match = re.search(r'from (.*) import (.*)', import_line)
                modules = [m.strip() for m in match.groups()[1].split(',')]
                __import__(match.groups()[0], global_variables, local_variables, modules, -1)
                
        @staticmethod
        def import_file(full_filename):
            path, filename = os.path.split(full_filename)
            
            # add settings dir from path
            sys.path.insert(0, path)
            
            # read imports from config file
#            try:
#                modules = FileConfig.SettingsFile.get_file_imports(full_filename)
#                for module in modules:
#                    FileConfig.SettingsFile.exec_import(module, globals(), locals())
#            except Exception, e:
#                raise Exception("error executing imports from config file '%s': %s" % (filename, str(e)))

            # read config file
            local_variables = locals()
            local_variables['__file__'] = full_filename
            try:
                execfile(full_filename, globals(), local_variables)
            except IOError:
                raise Exception("%s: file not found" % filename)
            except Exception, e:
                raise Exception("error interpreting config file '%s': %s" % (filename, str(e)))

            # remove settings dir from path
            sys.path.remove(path)
            
            return local_variables
    
    def __init__(self, config_file="simple-db-migrate.conf"):
        self._config = {}
        self.put("db_version_table", self.DB_VERSION_TABLE)
        
        # read configuration
        settings = FileConfig.SettingsFile.import_file(config_file)
        
        config_path = os.path.split(config_file)[0]
        self.put("db_host", self.get_variable(settings, 'DATABASE_HOST', 'HOST'))
        self.put("db_user", self.get_variable(settings, 'DATABASE_USER', 'USERNAME'))
        self.put("db_password", self.get_variable(settings, 'DATABASE_PASSWORD', 'PASSWORD'))
        self.put("db_name", self.get_variable(settings, 'DATABASE_NAME', 'DATABASE'))
        
        migrations_dir = self.get_variable(settings, 'DATABASE_MIGRATIONS_DIR', 'MIGRATIONS_DIR')
        self.put("migrations_dir", self._parse_migrations_dir(migrations_dir, config_path))
        
    def get_variable(self, local_variables_dict, name, old_name):
        if name in local_variables_dict or old_name in local_variables_dict:
            return local_variables_dict.get(name, local_variables_dict.get(old_name))
        else:
            raise NameError("config file error: name '%s' is not defined" % name)

class InPlaceConfig(Config):

    def __init__(self, db_host, db_user, db_password, db_name, migrations_dir, db_version_table=''):
        if not db_version_table or db_version_table == '':
            db_version_table = self.DB_VERSION_TABLE
        self._config = {
            "db_host": db_host,
            "db_user": db_user,
            "db_password": db_password,
            "db_name": db_name,
            "db_version_table": db_version_table,
            "migrations_dir": self._parse_migrations_dir(migrations_dir)
        }
