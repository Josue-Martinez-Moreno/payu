# coding: utf-8
"""
The payu interface for GFDL models based on FMS
-------------------------------------------------------------------------------
Contact: Marshall Ward <marshall.ward@anu.edu.au>
-------------------------------------------------------------------------------
Distributed as part of Payu, Copyright 2011 Marshall Ward
Licensed under the Apache License, Version 2.0
http://www.apache.org/licenses/LICENSE-2.0
"""

# Standard Library

from collections import defaultdict
import os
import resource as res
import sys
import shlex
import shutil as sh
import subprocess as sp

# Local
from payu.models.model import Model


class Fms(Model):

    def __init__(self, expt, name, config):

        # payu initalisation
        super(Fms, self).__init__(expt, name, config)

    def set_model_pathnames(self):

        super(Fms, self).set_model_pathnames()

        # Define local FMS directories
        self.work_restart_path = os.path.join(self.work_path, 'RESTART')
        self.work_input_path = os.path.join(self.work_path, 'INPUT')
        self.work_init_path = self.work_input_path

    def archive(self, **kwargs):

        # Remove the 'INPUT' path
        cmd = 'rm -rf {}'.format(self.work_input_path)
        sp.check_call(shlex.split(cmd))

        # Archive restart files before processing model output
        if os.path.isdir(self.restart_path):
            os.rmdir(self.restart_path)

        cmd = 'mv {} {}'.format(self.work_restart_path, self.restart_path)
        sp.check_call(shlex.split(cmd))

    def collate(self):

        # Set the stacksize to be unlimited
        res.setrlimit(res.RLIMIT_STACK, (res.RLIM_INFINITY, res.RLIM_INFINITY))

        # Locate the FMS collation tool
        mppnc_path = None
        for f in os.listdir(self.expt.lab.bin_path):
            if f.startswith('mppnccombine'):
                mppnc_path = os.path.join(self.expt.lab.bin_path, f)
                break
        assert mppnc_path

        # Import list of collated files to ignore
        collate_ignore = self.expt.config.get('collate_ignore')
        if collate_ignore is None:
            collate_ignore = []
        elif type(collate_ignore) != list:
            collate_ignore = [collate_ignore]

        # Generate collated file list and identify the first tile
        tile_fnames = [f for f in os.listdir(self.output_path)
                       if f[-4:].isdigit() and f[-8:-4] == '.nc.']

        mnc_tiles = defaultdict(list)
        for t_fname in tile_fnames:
            t_base, t_ext = os.path.splitext(t_fname)
            t_ext = t_ext.lstrip('.')

            # Skip any files listed in the ignore list
            if t_base in collate_ignore:
                continue

            mnc_tiles[t_base].append(t_fname)

        # Collate each tileset into a single file
        for nc_fname in mnc_tiles:
            nc_path = os.path.join(self.output_path, nc_fname)

            # Remove the collated file if it already exists, since it is
            # probably from a failed collation attempt
            # TODO: Validate this somehow
            if os.path.isfile(nc_path):
                os.remove(nc_path)

            # Switch to the output directory, to reduce cmd characters
            prior_wd = os.getcwd()
            os.chdir(self.output_path)

            cmd = '{} -r -64 {} {}'.format(mppnc_path, nc_fname,
                                           ' '.join(mnc_tiles[nc_fname]))
            print(cmd)
            sp.check_call(shlex.split(cmd))

            os.chdir(prior_wd)