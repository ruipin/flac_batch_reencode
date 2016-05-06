#!/usr/bin/python

# FLAC Batch Re-encode script
# Version 1.0 - 6 May 2016
#
# Author: Rui Pinheiro

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

import sys, getopt, logging, os, fnmatch, subprocess

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
	print "Usage: %s [-h] [-f <folder>] [-m <mask>] [--check-vendor] [-v [--vendor-string <vendor>]] [--no-verify]" % argv_0
	print "\t-h / --help     :    Show this help."
	print "\t-f / --folder   :    Root folder path for recursive search (default: '.')."
	print "\t-m / --mask     :    File mask (default: '*.flac')."
	print "\t-v / --vendor   :    Skip file if vendor string matches '<vendor>' (requires metaflac)."
	print "\t--vendor-string :    Desired vendor string for '-v' (default: '%s')." % DEFAULT_VENDOR_STRING
	print "\t--no-verify     :    Do not verify output for encoding errors before overwriting original files. Faster, but in rare cases could result in corrupt files."
	print "\t--flac          :    Path to the 'flac' executable (default: 'flac')."
	print "\t--metaflac      :    Path to the 'metaflac' executable (only required if using '-v', default: 'metaflac')."
	sys.exit(exit_val)

def main(argv):
	init_logging()

	# Parse opts
	folder = '.'
	mask = '*.flac'
	check_vendor = False
	verify = True
	vendor_string = DEFAULT_VENDOR_STRING
	flac_path = FLAC_EXECUTABLE
	metaflac_path = METAFLAC_EXECUTABLE
	
	logging.debug('Argument List: %s', str(argv))
	
	try:
		opts, args = getopt.getopt(argv[1:],'hf:m:v',['help','folder=','mask=','vendor','vendor-string=','no-verify','flac=','metaflac='])
	except getopt.GetoptError:
		usage(argv[0], 2)
	for opt, arg in opts:
		if opt in ("-h", "--help"):
			usage(argv[0], 0)
		elif opt in ("-f", "--folder"):
			folder = arg
		elif opt in ("-m", "--mask"):
			mask = arg
		elif opt in ("-v", "--vendor"):
			check_vendor = True
		elif opt == "--vendor-string":
			vendor_string = arg
		elif opt == "--no-verify":
			verify = False
		elif opt == "--flac":
			flac_path = arg
		elif opt == "--metaflac":
			metaflac_path = arg
	
	logging.debug("folder='%s'; mask='%s'; check_vendor=%s", folder, mask, check_vendor)
	
	# Start main process
	files = get_file_list(folder, mask, check_vendor, vendor_string, metaflac_path)
	
	if len(files) > 0:
		reencode_files(files, folder, verify, flac_path)
	
	logging.info('Finished.')

def compare_vendor_string(path, vendor_string, metaflac_path):
	logger = logging.getLogger('compare_vendor_string')
	logger.setLevel(logging.INFO)
	
	logger.debug("Obtaining vendor string of file '%s'...", path)
	
	cmd = [metaflac_path, '--show-vendor-tag', path]
	cmd_out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
	vendor = cmd_out.strip()
	
	res = (vendor == vendor_string)
	logger.debug("Vendor: '%s' %s", vendor, 'matches desired' if res else 'differs from desired')
	
	return 

def get_file_list(folder, mask, check_vendor, vendor_string, metaflac_path):
	logger = logging.getLogger('get_file_list')
	logger.setLevel(logging.INFO)
	
	out_files = []
	
	logger.info("Searching '%s' recursively for files matching mask '%s'...", folder, mask)
	if check_vendor:
		logger.info("Will skip files that match vendor string '%s'.", vendor_string)
	
	for root, dirs, files in os.walk(folder, followlinks=True):
		logger.debug("Found file(s) in '%s': %s", root, str(files))
		for name in files:
			if fnmatch.fnmatch(name, mask):
				path = os.path.join(root, name)
				logger.debug("File '%s' matches mask", path)
				
				if check_vendor and not compare_vendor_string(path, vendor_string, metaflac_path):
					logger.debug("Skipped '%s': Matches desired vendor string.", name)
					continue
				
				out_files.append(path)
	
	logger.info("Found %d file(s).", len(out_files))
	logger.debug("Found file(s): %s", str(out_files))
	return out_files

def reencode_file(file, verify, flac_path):
	logger = logging.getLogger('reencode_file')
	logger.setLevel(logging.INFO)
	
	cmd = [flac_path, file, '--force', '--best']
	if verify:
		cmd.append('-V')
	if SILENT_FLAC:
		cmd.append('-s')
	
	try:
		cmd_out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).strip()
	except subprocess.CalledProcessError as e:                           
		logger.critical("Exited with error code: %d\n%s", e.returncode, e.output)
		sys.exit(-2)
	
	logger.debug("Command '%s':\n%s", cmd, cmd_out)
	
	if SILENT_FLAC and cmd_out:
		logger.warning("Output was not empty: %s", cmd_out)

def reencode_files(files, root_folder, verify, flac_path):
	logger = logging.getLogger('reencode_files')
	logger.setLevel(logging.INFO)
	
	total = len(files)
	total_len = len(str(total))
	i = 0
	
	for file in files:
		i += 1
		i_padded = str(i).rjust(total_len, ' ')
		i_pct = float(i) / total * 100
		rel_path = os.path.relpath(file, root_folder)
		print "%s/%d (%d%%): Re-encoding '%s'..." % (i_padded, total, i_pct, rel_path)
		
		reencode_file(file, verify, flac_path)

if __name__ == "__main__":
	main(sys.argv)