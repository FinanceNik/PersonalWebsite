import sqlite3
import datetime
import requests


def create_database():
    connection = sqlite3.connect('staging.db')
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contactRequests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission TEXT NOT NULL,
            firstname TEXT NOT NULL,
            lastname TEXT NOT NULL,
            country TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL
        )
    ''')

    # Commit the changes and close the connection
    connection.commit()
    connection.close()


def insert_contact_request(firstname, lastname, country, email, message):
    connection = sqlite3.connect('staging.db')
    cursor = connection.cursor()

    cursor.execute('''
        INSERT INTO contactRequests (submission, firstname, lastname, country, email, message)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.datetime.now(), firstname, lastname, country, email, message))

    # Commit the changes and close the connection
    connection.commit()
    connection.close()


def get_database():
    connection = sqlite3.connect('staging.db')
    cursor = connection.cursor()

    cursor.execute('''
        SELECT * FROM contactRequests
    ''')

    # Fetch all the results
    results = cursor.fetchall()

    # Commit the changes and close the connection
    connection.commit()
    connection.close()

    return results


# print(get_database())

