# -*- coding: utf-8 -*-
"""
Tools to get files from the remote folder
"""

from aiida.common.folders import SandboxFolder


def list_remote_files(node):
    """Open an ssh connection and return the list of files in the remote"""
    computer = node.outputs.remote_folder.computer
    remote_path = node.outputs.remote_folder.get_remote_path()
    transport = computer.get_transport()
    with transport:
        remote_file_list = transport.listdir(remote_path)
    return remote_file_list


def get_file_content_from_remote(node, fname):
    """copy a text file from the remote to a temporary dir and load it from there"""
    with SandboxFolder() as tempfolder:
        with tempfolder.open('tempfile', 'w') as f:
            try:
                node.outputs.remote_folder.getfile(fname, f.name)
                has_outfile = True
            except:  # pylint: disable=bare-except
                has_outfile = False
        if has_outfile:
            with tempfolder.open('tempfile', 'r') as f:
                contents = f.readlines()
        else:
            raise ValueError(f"File '{fname}' not found on remote")

        return contents
