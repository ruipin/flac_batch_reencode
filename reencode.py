#!python3

""" FLAC Batch Re-encode

    A Python 3 script for batch parallel re-encoding many FLAC files.
    This is useful to make sure that your whole FLAC library is using
    the latest version of the FLAC encoder, with maximum compression.

    Version 1.3 - 29 Jun 2019
    Author: Rui Pinheiro
"""

"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys, codecs, getopt, logging, os, fnmatch, subprocess, time, multiprocessing

######################################
# Logging
def init_logging():
    # Configure root logger
    logging.root.setLevel(logging.INFO)

    # create console handler
    ch = logging.StreamHandler(sys.stdout)
    ch_formatter = logging.Formatter('%(asctime)s [%(name)s:%(levelname)s] %(message)s')
    ch.setFormatter(ch_formatter)
    logging.root.addHandler(ch)

# Constants
FLAC_EXECUTABLE = './flac'
REENCODE_TIMEOUT = None

# Debug constants
SILENT_FLAC = True


######################################
# Main Implementation
def usage(argv_0, exit_val):
    print("FLAC Batch Reencode\n")
    print("A Python script for batch re-encoding many *.flac files recursively. This is useful to make sure that your whole FLAC library is using the latest version of the FLAC encoder, with maximum compression.\n")
    print("Usage: %s [-h] [-f <folder>] [-m <mask>] [-p <n_parallel>] [--no-verify] [--flac <flac-path>]" % argv_0)
    print("\t-h / --help     :    Show this help.")
    print("\t-f / --folder   :    Root folder path for recursive search (default: '.').")
    print("\t-m / --mask     :    File mask (default: '*.flac').")
    print("\t-p / --parallel :    Maximum simultaneous encoder processes (default: max([CPU count]-1,1) = %d)." % max(multiprocessing.cpu_count()-1,1))
    print("\t--no-verify     :    Do not verify output for encoding errors before overwriting original files. Faster, but in rare cases could result in corrupt files.")
    print("\t--flac          :    Path to the 'flac' executable (default: 'flac').")
    sys.exit(exit_val)

def main(argv):
    init_logging()

    # Parse opts
    global root_folder, file_mask, verify_output, flac_path, n_parallel
    root_folder = '.'
    file_mask = '*.flac'
    verify_output = True
    flac_path = FLAC_EXECUTABLE
    n_parallel = max(multiprocessing.cpu_count()-1,1)

    logging.debug('Argument List: %s', str(argv))

    try:
        opts, args = getopt.getopt(argv[1:],'hf:m:vp:',['help','folder=','mask=','no-verify','flac=','parallel='])
    except getopt.GetoptError:
        usage(argv[0], 2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage(argv[0], 0)
        elif opt in ("-f", "--folder"):
            root_folder = arg
        elif opt in ("-m", "--mask"):
            file_mask = arg
        elif opt == "--no-verify":
            verify_output = False
        elif opt == "--flac":
            flac_path = arg
        elif opt in ("-p", "--parallel"):
            try:
                n_parallel = int(arg)
            except:
                logging.critical("'%s <n_parallel>' must have a positive integer", opt)
                sys.exit(-4)
            if n_parallel <= 0:
                logging.critical("'%s <n_parallel>' must have a positive integer", opt)
                sys.exit(-4)

    # Start main process
    files = get_file_list(root_folder, file_mask)

    if len(files) > 0:
        reencode_files(files)

    logging.info('Finished.')

def get_file_list(root_folder, file_mask):
    """Recursively searches a folder for a specific file mask, and creates a list of all such files.

    Args:
        root_folder (str): Root folder for recursive search.
        file_mask (str): File mask using linux patterns (ex: '*.flac').

    Returns:
        List[str]: Paths of all files inside 'folder' matching 'mask'
    """

    logger = logging.getLogger('get_file_list')
    logger.setLevel(logging.INFO)

    out_files = []

    logger.info("Searching '%s' recursively for files matching mask '%s'...", root_folder, file_mask)

    for root, dirs, files in os.walk(root_folder, followlinks=True):
        logger.debug("Found file(s) in '%s': %s", root, str(files))
        for name in files:
            if fnmatch.fnmatch(name, file_mask):
                path = os.path.join(root, name)
                logger.debug("File '%s' matches mask", path)

                out_files.append(path)

    logger.info("Found %d file(s).", len(out_files))
    logger.debug("Found file(s): %s", str(out_files))
    return out_files



class ReencodeJob(object):
    def __init__(self, file):
        """Constructs a ReencodeJob for a file

        Args:
            file (str): Path of file to re-encode.
        """
        self.log = logging.getLogger('ReencodeJob')
        self.log.setLevel(logging.INFO)
    
        self.file = file

        
    def start(self):
        """Starts the re-encoding process for a file using 'flac <file> -V -s --force --best'
        """

        cmd = [flac_path, self.file, '--force', '--best']
        if verify_output:
            cmd.append('-V')
        if SILENT_FLAC:
            cmd.append('-s')

        self.start_time = time.time()
        
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    def finish(self):
        """Finishes the re-encoding process for a file. To be exact, checks whether an error occurred.

        Returns:
            bool: Whether 'proc' terminated successfuly.
        """
        (cmd_out, cmd_err) = self.proc.communicate()
        cmd_out = cmd_out.strip()
        cmd_err = cmd_err.strip()

        if self.proc.returncode != 0:
            self.log.critical("File '%s' exited with error code: %d\nSTDOUT:\n%s\nSTDERR: %s", self.file, self.proc.returncode, cmd_out, cmd_err)
            return False

        self.log.debug("File '%s' STDOUT:\n%s\nSTDERR: %s", self.file, cmd_out, cmd_err)

        if SILENT_FLAC and (cmd_out or cmd_err):
            if "Compression failed (ratio" not in cmd_err:
                self.log.warning("File '%s' - output was not empty:\nSTDOUT: %s\nSTDERR: %s", self.file, cmd_out, cmd_err)
            else:
                self.log.warning("File '%s': Could not compress further", self.file)

        return True
        
    def _remove_tmp(self):
        tmp_filename = self.file + ".tmp,fl-ac+en'c"
        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)
        
    def wait(self):
        """Wait for the re-encode job to finish"""
        self.proc.wait()
        self._remove_tmp()

    def wait_communicate(self):
        """Wait for the re-encode job to finish"""
        self.proc.communicate()
        self._remove_tmp()

    def poll(self):
        """Polls the process, and returns the error code (or None if not yet finished)"""
        result = self.proc.poll()
        
        if REENCODE_TIMEOUT is not None and result is None:
            delta_time = time.time() - self.start_time
            if delta_time > REENCODE_TIMEOUT:
                raise RuntimeError("Job timed out: {}".format(self.file))

        return result
        
    def __repr___(self):
        return str(self.file)
        
    def __str__(self):
        return str(self.file)


class ReencodeJobList(object):
    def __init__(self):
        self.log = logging.getLogger('ReencodeJobList')
        self.log.setLevel(logging.INFO)

        self.jobs = []

    def start(self, file):
        job = ReencodeJob(file)
        self.jobs.append(job)
        
        job.start()
        
    def finish(self, job, wait=False):
        """Check if a finished process was successful, or exit the application with an error code.

        Args:
            procs (list[tuple[string, Popen]]): File names and corresponding Popen objects
            proc_typle (tuple[string, Popen]): File name and Popen object to check (must be a member of 'procs')
        """
        # Sanity check
        if job not in self.jobs:
            raise ValueError("'job' is not owned by the current 'ReencodeJobsList' instance")
        
        if not wait:
            # Check if it has finished, otherwise return
            if job.poll() is None:
                return False

        # Remove from list since it has finished
        old_len = len(self.jobs)
        self.jobs.remove(job)
        if len(self.jobs) >= old_len:
            raise RuntimeError("Could not remove job")

        # Check if job fails and we need to restart it (or exit)
        success = job.finish()
        if not success:
            # Ask user what they want to do
            has_input = False
            user_input = ""
            while not has_input:
                user_input = raw_input("Encoding failed. Do you wish to [r]etry, [s]kip or [a]bort? ").lower()
                if len(user_input) != 1 or user_input not in ('r', 's', 'a'):
                    print("Invalid answer '%s'." % (user_input))
                else:
                    has_input = True

            # abort
            if user_input == 'a':
                self.wait()
                logger.critical("Exiting.")
                sys.exit(-6)

            # retry
            elif user_input == 'r':
                self.jobs.append(job)
                job.start()

        # Done
        return True
    
    def wait(self):
        """Wait for processes in 'jobs' to terminate, and if necessary removes the temporary files created by the processes.

        Args:
            jobs (list[ReencodeJob]): Jobs to wait for
        """
        for job in self.jobs:
            job.wait()
            
    def poll(self):
        found = False
        for job in self.jobs:
            found |= self.finish(job)
        return found
        
    def communicate(self):
        for job in self.jobs:
            self.finish(job, wait=True)
        
    def __len__(self):
        return len(self.jobs)
        
    def __repr___(self):
        return str(self.jobs)
        
    def __str__(self):
        return str(self.jobs)


def reencode_files(files):
    """Re-encodes a list of files.

    Args:
        files (list[str]): List of file paths to re-encode.
    """

    logger = logging.getLogger('reencode_files')
    logger.setLevel(logging.INFO)

    total = len(files)
    total_len = len(str(total))
    i = 0

    jobs = ReencodeJobList()

    logger.info("Starting re-encode process using %d thread(s)...", n_parallel)

    try:
        for file in files:
            i += 1
            i_padded = str(i).rjust(total_len, ' ')
            i_pct = float(i) / total * 100
            rel_path = os.path.relpath(file, root_folder)
            print("%s/%d (%d%%): Re-encoding '%s'..." % (i_padded, total, i_pct, rel_path))

            jobs.start(file)

            # Limit number of processes to n_parallel
            # If limit is reached, wait until at least one finishes
            while len(jobs) >= n_parallel:
                if not jobs.poll():
                    time.sleep(1)

    except KeyboardInterrupt as e: # subprocesses also receive the signal
        logger.critical("Keyboard Interrupt (Ctrl-C) detected. Waiting for encoder(s) to cancel...")
        jobs.wait()
        logger.critical("Exiting.")
        sys.exit(-3)

    # Make sure all sub-processes exit before terminating
    jobs.wait()




if __name__ == "__main__":
    main(sys.argv)