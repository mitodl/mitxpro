"""Utility functions for ecommerce"""


def create_delete_rule(table_name):
    """Helper function to make SQL to create a rule to prevent deleting from the ecommerce table"""
    return f"CREATE RULE delete_protect AS ON DELETE TO ecommerce_{table_name} DO INSTEAD NOTHING"


def create_update_rule(table_name):
    """Helper function to make SQL to create a rule to prevent updating a row in the ecommerce table"""
    return f"CREATE RULE update_protect AS ON UPDATE TO ecommerce_{table_name} DO INSTEAD NOTHING"


def rollback_delete_rule(table_name):
    """Helper function to make SQL to create a rule to allow deleting from the ecommerce table"""
    return f"DROP RULE delete_protect ON ecommerce_{table_name}"


def rollback_update_rule(table_name):
    """Helper function to make SQL to create a rule to allow updating from the ecommerce table"""
    return f"DROP RULE update_protect ON ecommerce_{table_name}"
