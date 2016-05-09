#!/usr/bin/python

########################################################################
#######################  FLAC Batch Re-encode  #########################
# A Python 2.7 script for batch parallel re-encoding many FLAC files.  #
# This is useful to make sure that your whole FLAC library is using    #
# the latest version of the FLAC encoder, with maximum compression.    #
# Files can be skipped if the encoder matches a user-defined vendor    #
# string (i.e., they were already encoded using the latest FLAC        #
# encoder).                                                            #
#                                                                      #
# Version 1.1 - 9 May 2016                                             #
# Author: Rui Pinheiro                                                 #
########################################################################

########################################################################
# This program is free software: you can redistribute it and/or modify #
# it under the terms of the GNU General Public License as published by #
# the Free Software Foundation, either version 3 of the License, or    #
# (at your option) any later version.                                  #
#                                                                      #
# This program is distributed in the hope that it will be useful,      #
# but WITHOUT ANY WARRANTY; without even the implied warranty of       #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the        #
# GNU General Public License for more details.                         #
#                                                                      #
# You should have received a copy of the GNU General Public License    #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.#
########################################################################

import sys, getopt, logging, os, fnmatch, subprocess, time, multiprocessing

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
DEFAULT_VENDOR_STRING = 'reference libFLAC 1.3.1 20141125' # for '--vendor'
METAFLAC_EXECUTABLE = 'metaflac'
FLAC_EXECUTABLE = 'flac'

# Debug constants
SILENT_FLAC = True

######################################
# Main Implementation
def usage(argv_0, exit_val):
	print "FLAC Batch Reencode"
	print "A Python script for batch re-encoding many *.flac files recursively. This is useful to make sure that your whole FLAC library is using the latest version of the FLAC encoder, with maximum compression. Files can be skipped if the encoder matches a user-defined vendor string (i.e., they were already encoded using the latest FLAC encoder).\n"
	print "Usage: %s [-h] [-f <folder>] [-m <mask>] [-p <n_parallel>] [-v [--vendor-string <vendor>]] [--no-verify] [--flac <flac-path>] [--metaflac <metaflac-path>]" % argv_0
	print "\t-h / --help     :    Show this help."
	print "\t-f / --folder   :    Root folder path for recursive search (default: '.')."
	print "\t-m / --mask     :    File mask (default: '*.flac')."
	print "\t-p / --parallel :    Maximum simultaneous encoder processes (default: max([CPU count]-1,1) = %d)." % max(multiprocessing.cpu_count()-1,1)
	print "\t-v / --vendor   :    Skip file if vendor string matches '<vendor>' (requires metaflac)."
	print "\t--vendor-string :    Desired vendor string for '-v' (default: '%s')." % DEFAULT_VENDOR_STRING
	print "\t--no-verify     :    Do not verify output for encoding errors before overwriting original files. Faster, but in rare cases could result in corrupt files."
	print "\t--flac          :    Path to the 'flac' executable (default: 'flac')."
	print "\t--metaflac      :    Path to the 'metaflac' executable (only required if using '-v', default: 'metaflac')."
	sys.exit(exit_val)

def main(argv):
	init_logging()

	# Parse opts
	global root_folder, file_mask, check_vendor, verify_output, vendor_string, flac_path, metaflac_path, n_parallel
	root_folder = '.'
	file_mask = '*.flac'
	check_vendor = False
	verify_output = True
	vendor_string = DEFAULT_VENDOR_STRING
	flac_path = FLAC_EXECUTABLE
	metaflac_path = METAFLAC_EXECUTABLE
	n_parallel = max(multiprocessing.cpu_count()-1,1)
	
	logging.debug('Argument List: %s', str(argv))
	
	try:
		opts, args = getopt.getopt(argv[1:],'hf:m:vp:',['help','folder=','mask=','vendor','vendor-string=','no-verify','flac=','metaflac=','parallel='])
	except getopt.GetoptError:
		usage(argv[0], 2)
	for opt, arg in opts:
		if opt in ("-h", "--help"):
			usage(argv[0], 0)
		elif opt in ("-f", "--folder"):
			root_folder = arg
		elif opt in ("-m", "--mask"):
			file_mask = arg
		elif opt in ("-v", "--vendor"):
			check_vendor = True
		elif opt == "--vendor-string":
			vendor_string = arg
		elif opt == "--no-verify":
			verify_output = False
		elif opt == "--flac":
			flac_path = arg
		elif opt == "--metaflac":
			metaflac_path = arg
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

def compare_vendor_string(path):
	"""Compares the vendor string of a certain file with the desired vendor string.
	Uses 'metaflac --show-vendor-tag'

	Args:
		path (str): Path of file to check.

	Returns:
		bool: True if vendor string matches, False otherwise.
	"""
	
	logger = logging.getLogger('compare_vendor_string')
	logger.setLevel(logging.INFO)
	
	logger.debug("Obtaining vendor string of file '%s'...", path)
	
	cmd = [metaflac_path, '--show-vendor-tag', path]
	cmd_out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
	vendor = cmd_out.strip()
	
	res = (vendor == vendor_string)
	logger.debug("Vendor: '%s' %s", vendor, 'matches desired' if res else 'differs from desired')
	
	return res

def get_file_list(root_folder, file_mask):
	"""Recursively searches a folder for a specific file mask, and creates a list of all such files.

	Args:
		root_folder (str): Root folder for recursive search.
		file_mask (str): File mask using linux patterns (ex: '*.flac').

	Returns:
		List[str]: Paths of all files inside 'folder' matching 'mask', with matching vendor string (if 'check_vendor' is true).
	"""
	
	logger = logging.getLogger('get_file_list')
	logger.setLevel(logging.INFO)
	
	out_files = []
	
	logger.info("Searching '%s' recursively for files matching mask '%s'...", root_folder, file_mask)
	if check_vendor:
		logger.info("Will skip files that match vendor string '%s'.", vendor_string)
	
	for root, dirs, files in os.walk(root_folder, followlinks=True):
		logger.debug("Found file(s) in '%s': %s", root, str(files))
		for name in files:
			if fnmatch.fnmatch(name, file_mask):
				path = os.path.join(root, name)
				logger.debug("File '%s' matches mask", path)
				
				if check_vendor and not compare_vendor_string(path):
					logger.debug("Skipped '%s': Matches desired vendor string.", name)
					continue
				
				out_files.append(path)
	
	logger.info("Found %d file(s).", len(out_files))
	logger.debug("Found file(s): %s", str(out_files))
	return out_files

def start_reencode_file(file):
	"""Starts the re-encoding process for a file using 'flac <file> -V -s --force --best'

	Args:
		file (str): Path of file to re-encode.

	Returns:
		Tuple[str, Popen]: File name and corresponding Popen object
	"""
	
	logger = logging.getLogger('start_reencode_file')
	logger.setLevel(logging.INFO)
	
	cmd = [flac_path, file, '--force', '--best']
	if verify_output:
		cmd.append('-V')
	if SILENT_FLAC:
		cmd.append('-s')
	
	proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	return (file, proc)

def finish_reencode_file(file, proc):
	"""Finishes the re-encoding process for a file. To be exact, checks whether an error occurred.

	Args:
		file (str): Path of re-encoded file.
		proc (Popen): Popen object of the re-encoding subprocess for 'file'.
	
	Returns:
		bool: Whether 'proc' terminated successfuly.
	"""
	
	logger = logging.getLogger('finish_reencode_file')
	logger.setLevel(logging.INFO)
	
	(cmd_out, cmd_err) = proc.communicate()
	
	if proc.returncode != 0:
		logger.critical("File '%s' exited with error code: %d\nSTDOUT:\n%s\nSTDERR: %s", file, proc.returncode, cmd_out, cmd_err)
		return False
	
	cmd_out = cmd_out.strip()
	cmd_err = cmd_err.strip()
	
	logger.debug("File '%s' STDOUT:\n%s\nSTDERR: %s", file, cmd_out, cmd_err)
	
	if SILENT_FLAC and (cmd_out or cmd_err):
		logger.warning("File '%s' - output was not empty:\nSTDOUT: %s\nSTDERR: %s", file, cmd_out, cmd_err)
	
	return True

def wait_for_terminate(procs):
	"""Wait for processes in 'procs' to terminate, and if necessary removes the temporary files created by the processes.

	Args:
		procs (list[tuple[string, Popen]]): File names and corresponding Popen objects
	"""
	
	for (file, proc) in procs:
		proc.wait()
		tmp_filename = file + ".tmp,fl-ac+en'c"
		if os.path.exists(tmp_filename):
			os.remove(tmp_filename)

def check_proc_success(procs, proc_tuple):
	"""Check if a finished process was successful, or exit the application with an error code.

	Args:
		procs (list[tuple[string, Popen]]): File names and corresponding Popen objects
		proc_typle (tuple[string, Popen]): File name and Popen object to check (must be a member of 'procs')
	"""
	logger = logging.getLogger('check_proc_success')
	logger.setLevel(logging.INFO)
	
	(file, proc) = proc_tuple
	success = finish_reencode_file(file, proc)
	procs.remove(proc_tuple)
	if not success:
		wait_for_terminate(procs)
		logger.critical("Exiting.")
		sys.exit(-6)

def reencode_files(files):
	"""Re-encodes a list of files.

	Args:
		files (list[str]): List of file paths to re-encode.
	
	Returns:
		bool: Whether 'proc' terminated successfuly.
	"""
	
	logger = logging.getLogger('reencode_files')
	logger.setLevel(logging.INFO)
	
	total = len(files)
	total_len = len(str(total))
	i = 0
	
	procs = []
	
	logger.info("Starting re-encode process using %d thread(s)...", n_parallel)
	
	try:
		for file in files:
			i += 1
			i_padded = str(i).rjust(total_len, ' ')
			i_pct = float(i) / total * 100
			rel_path = os.path.relpath(file, root_folder)
			print "%s/%d (%d%%): Re-encoding '%s'..." % (i_padded, total, i_pct, rel_path)
			
			procs.append(start_reencode_file(file))
			
			if n_parallel == 1: # Avoid busy loop logic
				cur_tuple = procs[0]
				(file, proc) = cur_tuple
				proc.wait()
				check_proc_success(procs, cur_tuple)
			else:
				# Limit number of processes to n_parallel
				# If limit is reached, wait until at least one finishes
				while len(procs) >= n_parallel:
					found = False
					for j, cur_tuple in enumerate(procs):
						(file, proc) = cur_tuple
						returncode = proc.poll()
						if returncode != None:
							check_proc_success(procs, cur_tuple)
							found = True
					if not found:
						time.sleep(1)
	
	except KeyboardInterrupt as e: # subprocesses also receive the signal
		logger.critical("Keyboard Interrupt (Ctrl-C) detected. Waiting for encoder(s) to cancel...")
		wait_for_terminate(procs)
		logger.critical("Exiting.")
		sys.exit(-3)
	
	# Make sure all sub-processes exit before terminating
	wait_for_terminate(procs)




if __name__ == "__main__":
	main(sys.argv)