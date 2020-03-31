#!/usr/bin/env python
#Luca Pinello 2020

import argparse
import sys
import sqlite3
from sqlite3 import Error
import RPi.GPIO as GPIO           # import RPi.GPIO module
import numpy as np


def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return conn


def create_table(conn):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """

    create_roasters_table_sql = """ CREATE TABLE IF NOT EXISTS roasters (
                                            id integer PRIMARY KEY,
                                            name text NOT NULL,
                                            heat_level integer NOT_NULL,
                                            fan_level integer NOT_NULL
                                        ); """


    try:
        c = conn.cursor()
        c.execute(create_roasters_table_sql)
    except Error as e:
        print(e)

def create_roaster(conn, roaster):
    """
    Create a new project into the projects table
    :param conn:
    :param roaster:
    :return: roaster id
    """
    sql = ''' INSERT INTO roasters(name,heat_level,fan_level)
              VALUES(?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, roaster)
    return cur.lastrowid


def select_all_roasters(conn):
    """
    Query all rows in the roasters table
    :param conn: the Connection object
    :return:
    """
    cur = conn.cursor()
    cur.execute("SELECT * FROM roasters")

    rows = cur.fetchall()

    for row in rows:
        print(row)

def get_roaster (conn,roaster_id=None):

    cur = conn.cursor()

    if roaster_id is None: #take the first one
        cur.execute("SELECT * FROM roasters")
    else:
        cur.execute("SELECT * FROM tasks WHERE priority=?", (roaster_id,))

    roaster= cur.fetchall()
    if roaster:
        return roaster[0]
    else:
        return None

def update_roaster(conn, roaster):
    """
    update priority, begin_date, and end date of a task
    :param conn:
    :param roaster:
    :return: roaster id
    """
    sql = ''' UPDATE roasters
              SET name = ? ,
                  heat_level = ? ,
                  fan_level = ?
              WHERE id = ?'''
    cur = conn.cursor()
    cur.execute(sql,roaster)
    conn.commit()


def set_fan_level(conn,new_fan_level,roaster_id=None):

    if new_fan_level>=0 and new_fan_level<=15:

        roaster_id,name,heat_level,fan_level=get_roaster(conn)
        update_roaster(conn,(name,heat_level,new_fan_level,roaster_id))
    else:

        raise Exception("Fan level value must be in [0-15]")



def set_heat_level(conn,new_heat_level,roaster_id=None,min_fan_level=3):

    roaster_id,name,heat_level,fan_level=get_roaster(conn)

    if fan_level<min_fan_level:
        raise Exception('Heat level control is disabled if fan is lower then %d' % min_fan_level)

    if new_heat_level>=0 and new_heat_level<=100:
        update_roaster(conn,(name,new_heat_level,fan_level,roaster_id))
    else:
        raise Exception("Heat level value must be in [0-100]")

def stop(conn):
    roaster_id,name,heat_level,fan_level=get_roaster(conn)
    update_roaster(conn,(name,0,0,roaster_id))


def cool(conn):
    roaster_id,name,heat_level,fan_level=get_roaster(conn)
    update_roaster(conn,(name,0,15,roaster_id))


class Roaster(object):

    def __init__(self,database_filename='roaster.db',FAN_PINS=[26,19,13,6],PWM_PIN=12,PWM_FQ=60  ):
        parser = argparse.ArgumentParser(
            description='Beast Roaster Control',
            usage='''roaster_control <command> [<args>]


--- B E A S T  Roaster Control ---

Luca Pinello - 2020

The available commands are:
   get_status  print the status of the roaster (fan and heat)
   set_fan     change fan level, values allowed are in [0-15]
   set_heat    change heat level, values allowed are in [0-100]
   cool        stop the heat and set the fan to maximum
   stop        stop fan and heat and reset the GPIO


''')

        #setting up the GPIO

        mode=GPIO.getmode()
        print (mode)

        if GPIO.getmode() is None:
            GPIO.setmode(GPIO.BCM)
            for p in FAN_PINS:
                GPIO.setup(p, GPIO.OUT)

            GPIO.setup(PWM_PIN, GPIO.OUT)
            self.pwm = GPIO.PWM(PWM_PIN,PWM_FQ )
            self.pwm.start(0)

        self.GPIO=GPIO
	self.FAN_PINS=FAN_PINS

        # create a database connection
        self.conn = create_connection(database_filename)

        # create tables
        if self.conn is not None:
            # create roasters table
            create_table(self.conn)
        else:
            print("Error! cannot create the database connection.")

        with self.conn:
            roaster=get_roaster(self.conn)
            if  roaster is None: #we create one if it doesn't exist.
                roaster = ('Beast', 0, 0);
                roaster_id = create_roaster(self.conn, roaster)

                self.fan_level=0
                self.heat_level=0
                self.name='Beast'
            else:
                _,self.name,self.heat_level,self.fan_level=roaster

        parser.add_argument('command', help='Subcommand to run')
        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail
        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print('Unrecognized command')
            parser.print_help()
            exit(1)
        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()


    def set_fan(self):
        parser = argparse.ArgumentParser(
            description='Change Fan Level')
        parser.add_argument('new_fan_level',type=int)
        args = parser.parse_args(sys.argv[2:])
        print('New fan level %d' %args.new_fan_level)
        set_fan_level(self.conn,args.new_fan_level)
        self.fan_level=args.new_fan_level

        for idx,bit in enumerate(list(np.binary_repr(15-self.fan_level,width=4))):
            print (self.FAN_PINS[idx],int(bit))
            self.GPIO.output(self.FAN_PINS[idx],int(bit))


    def set_heat(self):
        parser = argparse.ArgumentParser(
            description='Change Heat Level')
        parser.add_argument('new_heat_level',type=int)
        args = parser.parse_args(sys.argv[2:])
        print('New heat level %d' %args.new_heat_level)
        set_heat_level(self.conn,args.new_heat_level)
        self.heat_level=args.new_heat_level

        #self.pwm.start(self.heat_level)
        self.pwm.ChangeDutyCycle(self.heat_level)


    def get_status(self):
        parser = argparse.ArgumentParser(description='Get Roaster Status')
        print ("Fan level:%d Heat Level %d" %(self.fan_level,self.heat_level))


    def cool(self):
    	parser = argparse.ArgumentParser(description='Cranking up fan to cool ')
	cool(self.conn)

    def stop(self):
        parser = argparse.ArgumentParser(description='Stopping the roaster and cleaning up ')
        stop(self.conn)
        if self.GPIO.getmode() is not None:
            self.GPIO.cleanup()


if __name__ == '__main__':
    roaster=Roaster()
    roaster.conn.close()
