"""Utility functions for sheets app"""


def namedtuple_from_array(ntuple, values):
    return ntuple(**dict(zip(ntuple._fields, values)))
