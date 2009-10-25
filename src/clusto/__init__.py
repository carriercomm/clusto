

from schema import *


from drivers import DRIVERLIST, TYPELIST, Driver, ClustoMeta
from sqlalchemy.exceptions import InvalidRequestError
from sqlalchemy import create_engine


import drivers

import threading
import logging

driverlist = DRIVERLIST
typelist = TYPELIST


def connect(dsn, echo=False):
    """Connect to a given Clusto datastore.

    Accepts a dsn string.

    e.g. mysql://user:pass@example.com/clustodb
    e.g. sqlite:///somefile.db

    @param dsn: the clusto database URI
    """
    SESSION.configure(bind=create_engine(dsn, echo=echo))

def checkDBcompatibility(dbver):

    if dbver == VERSION:
        return True

def init_clusto():
    """Initialize a clusto database. """
    METADATA.create_all(SESSION.bind)
    SESSION.execute(CLUSTO_VERSIONING.insert().values())
    c = ClustoMeta()
    flush()
    commit()



def flush():
    """Flush changes made to clusto objects to the database."""

    SESSION.flush()
            


def clear():
    """Clear the changes made to objects in the current session. """

    SESSION.expunge_all()

def get_driver_name(name):
    "Return driver name given a name, Driver class, or Driver/Entity instance."

    if isinstance(name, str):
        if name in DRIVERLIST:
            return name
        else:
            raise NameError("driver name %s doesn't exist." % name)
    elif isinstance(name, type):
        return name._driver_name
    else:
        return name.driver

def get_type_name(name):

    if isinstance(name, str):
        if name in TYPELIST:
            return name
        else:
            raise NameError("driver name %s doesn't exist." % name)

    elif isinstance(name, type):
        return name._clusto_type
    else:
        return name.type
        

def get_driver(entity, ignore_driver_column=False):
    """Return the driver to use for a given entity """

    if not ignore_driver_column:
        if entity.driver in DRIVERLIST:
            return DRIVERLIST[entity.driver]

    return Driver

def get_entities(names=(), clusto_types=(), clusto_drivers=(), attrs=()):
    """Get entities matching the given criteria

    @param names: list of names to match
    @type names: list of strings
    
    @param clustotypes: list of clustotypes to match
    @param clustotypes: list of strings or Drivers

    @param clustodrivers: list of clustodrives to get
    @type clustodrives: list of strings or Drivers

    @param attrs: list of attribute parameters
    @type attrs: list of dictionaries with the following 
                 valid keys: key, number, subkey, value
    """
    
    query = SESSION.query(Entity)

    if names:
        query = query.filter(Entity.name.in_(names))

    if clusto_types:
        ctl = [get_type_name(n) for n in clusto_types]
        query = query.filter(Entity.type.in_(ctl))

    if clusto_drivers:
        cdl = [get_driver_name(n) for n in clusto_drivers]
        query = query.filter(Entity.driver.in_(cdl))

    if attrs:
        query = query.filter(Attribute.entity_id==Entity.entity_id)

        query = query.filter(or_(*[Attribute.queryarg(**args) 
                                   for args in attrs]))
        

    return [Driver(entity) for entity in query.all()]

    
def get_by_name(name):
    try:
        entity = SESSION.query(Entity).filter_by(name=name).one()

        retval = Driver(entity)
            
        return retval
    except InvalidRequestError:
        raise LookupError(name + " does not exist.")

get_by_attr = drivers.base.Driver.get_by_attr

def get_or_create(name, driver):
    try:
        obj = get_by_name(name)
    except LookupError:
        obj = driver(name)
        logging.info('Created %s' % obj)
    return obj

              
def rename(oldname, newname):
    """Rename an Entity from oldname to newname.

    THIS CAN CAUSE PROBLEMS IF NOT USED CAREFULLY AND IN ISOLATION FROM OTHER
    ACTIONS.
    """

    old = get_by_name(oldname)

    old.entity.name = newname


tl = threading.local()
tl.TRANSACTIONCOUNTER = 0

def begin_transaction():
    """Start a transaction

    If already in a transaction start a savepoint transaction.

    If allow_nested is False then an exception will be raised if we're already
    in a transaction.
    """
    global tl
    if SESSION.is_active:
        tl.TRANSACTIONCOUNTER += 1
        return None
    else:
        tl.TRANSACTIONCOUNTER += 1
        return SESSION.begin()

def rollback_transaction():
    """Rollback a transaction"""
    global tl

    if SESSION.is_active:
        SESSION.rollback()
        tl.TRANSACTIONCOUNTER -= 1
    
    
def commit():
    """Commit changes to the datastore"""
    global tl

    if SESSION.is_active:
        if tl.TRANSACTIONCOUNTER == 1:
            SESSION.commit()
        tl.TRANSACTIONCOUNTER -= 1
        flush()
            

def disconnect():
    SESSION.close()

def delete_entity(entity):
    """Delete an entity and all it's attributes and references"""
    try:
        begin_transaction()
        SESSION.delete(entity)
        commit()
    except Exception, x:
        rollback_transaction()
        raise x
    

    
