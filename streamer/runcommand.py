#Copyright 2009 Lorenzo Benfenati.
#
# This library is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library.  If not, see <http://www.gnu.org/licenses/>.
__author__ = "Lorenzo Benfenati"
__licence__ = "LGPL"

import subprocess
import platform
import types





WINDOWSEXE=['.EXE', '.BAT']

class BinNotFound(Exception):
    pass

def which(program):
    import os
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


class RunCommand:
    
    def __init__ (self, binpath):
        if (platform.system() == 'Windows' 
            and not binpath[-4:].upper() in WINDOWSEXE ):
            binpath += '.exe'
        self.binpath = which(binpath)
        if not self.binpath:
            raise BinNotFound
        
    def runcommand(self, argv):
        #argv without command in argv[0]
        #command = ' '.join([self.binpath, argv])
        self._run(argv)
        
    def _run (self, argv):
        if platform.system() == 'Windows':
            if type(argv) == types.ListType:
                argv= " ".join(argv)
            command = "\"%s\" %s"%(self.binpath, argv)
            self.go = subprocess.Popen (command ,
                              executable = self.binpath,
                              shell = False)
#                              stdin = subprocess.PIPE,
#                              stderr = subprocess.PIPE,
#                              stdout = subprocess.PIPE)
        else:
            if isinstance(argv, types.StringTypes):
                self.go = subprocess.Popen ("\"%s\" %s"%(self.binpath, argv),
                              executable = "/bin/bash",
                              shell = True)
                #,
                #              stdin = subprocess.PIPE,
                #              stderr = subprocess.PIPE,
                #              stdout = subprocess.PIPE)
            else:
                self.go = subprocess.Popen ([self.binpath]+ argv ,
                              shell = False,
                              close_fds=True,
                              )
                #              ,
                #              stdin = subprocess.PIPE,
                #              stderr = subprocess.PIPE,
                #              stdout = subprocess.PIPE)
                
        return self.go

    def wait(self):
        self.go.wait()
       
    
if __name__ == '__main__':
    pass 
