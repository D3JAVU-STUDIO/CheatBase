# This program imports the raw data in the csv files, manipulates it to make it alphabetical and
# organized, then adds the data to the openvgdb.sqlite database.
# Copyright Noah Keck - All Rights Reserved

import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

class Parser:

    def __init__(self):
        # Setup database connection
        self.dir = Path(__file__).parent.resolve()
        self.conn = sqlite3.connect(str(self.dir) + "/openvgdb.sqlite")
        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT systemShortName FROM SYSTEMS")
        self.systems = []
        for sys in self.cursor.fetchall():
            self.systems.append(sys[0])

    def detect_key_changes(oldmatrix: list, newmatrix: list, keypos: int = 0) -> dict:
        changes = {}
        for i, arr in enumerate(oldmatrix):
            changes[arr[keypos]] = newmatrix[i][keypos]
        return changes

    # Returns a tuple containing the sorted matrix and a dict showing the primary key changes
    def special_sort(matrix: list, key=None, keypos: int = 0) -> list:
        temp = sorted(matrix, key=key)
        changes = {}
        for i, arr in enumerate(temp, start=1):
            changes[arr[keypos]] = i
            temp[i-1][keypos] = i
        temp = (temp, changes)
        return temp

    # Using the key dictionary, updates the specied foreign key at the index keypos
    def cascade_primary_keys(matrix: list, key: dict, keypos: int) -> list:
        for arr in matrix:
            arr[keypos] = key[int(arr[keypos])]
        return matrix

    def parse_systems(self, organize: bool = False):
        # Import data
        print("Importing systems data from file.")
        filepath = str(self.dir) + "/raw_data/systems.csv"
        fullsystems = pd.read_csv(filepath, header=0, encoding='utf-8').values.tolist()

        # Rearrange data
        if organize:
            sortr = lambda arr: arr[1] # sort by systemName
            temp = Parser.special_sort(fullsystems, key=sortr)
            self.systems_parsekey = temp[1]
            fullsystems = temp[0] # gets the sorted matrix

        # Export to openvgdb database
        print("Starting on systems table.")
        self.cursor.execute("DROP TABLE IF EXISTS SYSTEMS")
        query = """
            CREATE TABLE SYSTEMS (
                systemID INTEGER
                    PRIMARY KEY AUTOINCREMENT,
                systemName TEXT NOT NULL,
                systemShortName TEXT NOT NULL,
                systemHeaderSizeBytes INTEGER,
                systemHashless INTEGER,
                systemHeader INTEGER,
                systemSerial TEXT,
                systemOEID TEXT
            )
        """
        self.cursor.execute(query)

        # Insert data
        query = """
            INSERT INTO SYSTEMS (systemID, systemName, systemShortName, systemHeaderSizeBytes, systemHashless, systemHeader, systemSerial, systemOEID)
            VALUES (:sysid, :sysname, :sysshortname, :sysheadersize, :syshash, :sysheader, :sysserial, :sysoeid)
        """
        self.cursor.executemany(query, fullsystems)

    def parse_regions(self, organize: bool = False):
        # Import data
        print("Importing regions data from file.")
        filepath = str(self.dir) + "/raw_data/regions.csv"
        regions = pd.read_csv(filepath, header=0, encoding='utf-8').values.tolist()

        # Rearrange data
        if organize:
            sortr = lambda arr: arr[1] # sort by regionName
            temp = Parser.special_sort(regions, key=sortr)
            self.regions_parsekey = temp[1]
            regions = temp[0] # gets the sorted matrix

        # Export to openvgdb database
        print("Starting on regions table.")
        self.cursor.execute("DROP TABLE IF EXISTS REGIONS")
        query = """
            CREATE TABLE REGIONS (
                regionID INTEGER
                    PRIMARY KEY AUTOINCREMENT,
                regionName TEXT NOT NULL
            )
        """
        self.cursor.execute(query)

        # Insert data
        query = """
            INSERT INTO REGIONS (regionID, regionName)
            VALUES (:regid, :regname)
        """
        self.cursor.executemany(query, regions)

    def parse_roms(self, organize: bool = False):
        # Import data
        print("Importing roms data from file.")
        roms = []
        for sys in self.systems:
            filepath = Path(str(self.dir) + "/raw_data/roms/" + sys + ".csv")
            if Path(filepath).is_file():
                df = pd.read_csv(filepath, header=0, encoding='utf-8').replace({np.nan: None})
                dat = df.values.tolist()
                roms.extend(dat)

        # Rearrange data
        if hasattr(self, "systems_parsekey"):
            roms = Parser.cascade_primary_keys(roms, self.systems_parsekey, keypos=1)
        if hasattr(self, "regions_parsekey"):
            roms = Parser.cascade_primary_keys(roms, self.regions_parsekey, keypos=2)

        if organize:
            sortr = lambda arr: (arr[1], arr[7]) # sort by systemID, romFileName
            temp = Parser.special_sort(roms, key=sortr)
            self.roms_parsekey = temp[1]
            roms = temp[0] # gets the sorted matrix

        # Export to openvgdb database
        print("Starting on roms table.")
        self.cursor.execute("DROP TABLE IF EXISTS ROMs")
        query = """
            CREATE TABLE ROMs (
                romID INTEGER
            		PRIMARY KEY AUTOINCREMENT,
            	systemID INTEGER NOT NULL,
            	regionID INTEGER NOT NULL,
            	romHashCRC TEXT,
            	romHashMD5 TEXT,
            	romHashSHA1 TEXT,
            	romSize INTEGER,
            	romFileName TEXT NOT NULL,
            	romExtensionlessFileName TEXT NOT NULL,
            	romParent TEXT,
            	romSerial TEXT,
            	romHeader TEXT,
            	romLanguage TEXT,
            	romDumpSource TEXT NOT NULL,
            	FOREIGN KEY (systemID)
                    REFERENCES SYSTEMS (systemID)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
                FOREIGN KEY (regionID)
                    REFERENCES REGIONS (regionID)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
            )
        """
        self.cursor.execute(query)

        # Insert data
        query = """
            INSERT INTO ROMs (romID, systemID, regionID, romHashCRC, romHashMD5, romHashSHA1, romSize, romFileName, romExtensionlessFileName, romParent, romSerial, romHeader, romLanguage, romDumpSource)
            VALUES (:romid, :sysid, :regionid, :romhashcrc, :romhashmd5, :romhashsha1, :romsize, :romname, :romaltname, :romparent, :romserial, :romhead, :romlang, :romdump)
        """
        self.cursor.executemany(query, roms)

    def parse_releases(self, organize: bool = False):
        # Import data
        print("Importing releases data from file.")
        releases = []
        for sys in self.systems:
            filepath = Path(str(self.dir) + "/raw_data/releases/" + sys + ".csv")
            if Path(filepath).is_file():
                df = pd.read_csv(filepath, header=0, encoding='utf-8').replace({np.nan: None})
                releases.extend(df.values.tolist())

        # Rearrange data
        if hasattr(self, "roms_parsekey"):
            releases = Parser.cascade_primary_keys(releases, self.roms_parsekey, keypos=0)

        if organize:
            sortr = lambda arr: (arr[0], arr[2]) # sort by romID, regionLocalizedID
            releases.sort(key=sortr)

        # Export to openvgdb database
        print("Starting on releases table.")
        self.cursor.execute("DROP TABLE IF EXISTS RELEASES")
        query = """
            CREATE TABLE RELEASES (
                releaseID INTEGER
            		PRIMARY KEY AUTOINCREMENT,
            	romID INTEGER NOT NULL,
            	releaseTitleName TEXT NOT NULL,
            	regionLocalizedID INTEGER NOT NULL,
            	releaseCoverFront TEXT,
            	releaseCoverBack TEXT,
            	releaseCoverCart TEXT,
            	releaseCoverDisc TEXT,
            	releaseDescription TEXT,
            	releaseDeveloper TEXT,
            	releasePublisher TEXT,
            	releaseGenre TEXT,
            	releaseDate TEXT,
            	releaseReferenceURL TEXT,
            	releaseReferenceImageURL TEXT,
            	FOREIGN KEY (romID)
                    REFERENCES ROMs (romID)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
            )
        """
        self.cursor.execute(query)

        # Insert data
        query = """
            INSERT INTO RELEASES (romID, releaseTitleName, regionLocalizedID, releaseCoverFront, releaseCoverBack, releaseCoverCart, releaseCoverDisc, releaseDescription, releaseDeveloper, releasePublisher, releaseGenre, releaseDate, releaseReferenceURL, releaseReferenceImageURL)
            VALUES (:romid, :titlename, :regionid, :coverfront, :coverback, :covercart, :coverdisc, :releasedesc, :releasedev, :releasepubl, :releasegenre, :releasedate, :releaseurl, :releaseimgurl)
        """
        self.cursor.executemany(query, releases)

    def parse_cheats(self, organize: bool = False):
        # Import data
        print("Importing cheats data from file.")
        #convertkeys = {0: int, } # used for assigning the correct data types to each column
        allcheats = []
        for sys in self.systems:
            filepath = Path(str(self.dir) + "/raw_data/cheats/" + sys + ".csv")
            if Path(filepath).is_file():
                df = pd.read_csv(filepath, header=0, encoding='utf-8').replace({np.nan: None})
                allcheats.extend(df.values.tolist())

        filepath = str(self.dir) + "/raw_data/cheat_devices.csv"
        cheat_devices = pd.read_csv(filepath, header=0, encoding='utf-8').values.tolist()

        filepath = str(self.dir) + "/raw_data/cheat_categories.csv"
        cheat_categories = pd.read_csv(filepath, header=0, encoding='utf-8').values.tolist()

        # Rearrange data - In the future maybe write my own data structure to cascade the primary keys more easily
        # Checks for other changed keys and cascades the changes
        if hasattr(self, "systems_parsekey"):
            cheat_devices = Parser.cascade_primary_keys(cheat_devices, self.systems_parsekey, keypos=1)
        if hasattr(self, "roms_parsekey"):
            allcheats = Parser.cascade_primary_keys(allcheats, self.roms_parsekey, keypos=0)

        # Alphabetize, organize, etc.
        if organize:
            sortr = lambda arr: arr[1] # sort by cheatCategory
            temp = Parser.special_sort(cheat_categories, key=sortr)
            self.cheat_categories_parsekey = temp[1]
            cheat_categories = temp[0] # gets the sorted matrix

            sortr = lambda arr: (arr[1], arr[2]) # sort by systemID, cheatDeviceName
            temp = Parser.special_sort(cheat_devices, key=sortr)
            self.cheat_devices_parsekey = temp[1]
            cheat_devices = temp[0] # remove last element since that's the changes key

            allcheats = Parser.cascade_primary_keys(allcheats, self.cheat_categories_parsekey, keypos=6)
            allcheats = Parser.cascade_primary_keys(allcheats, self.cheat_devices_parsekey, keypos=8)

            sortr = lambda arr: (arr[0], arr[8], arr[5] or "", arr[6], arr[1]) # sort by romID, cheatDeviceID, cheatFolderName, cheatCategoryID, cheatName
            allcheats.sort(key=sortr)

        # Export to openvgdb database
        print("Starting on cheat tables.")
        self.cursor.executescript("DROP TABLE IF EXISTS CHEATS; DROP TABLE IF EXISTS CHEAT_DEVICES; DROP TABLE IF EXISTS CHEAT_CATEGORIES") # drop cheat tables if they exist
        query = """
            CREATE TABLE CHEAT_DEVICES (
                cheatDeviceID INTEGER
                    PRIMARY KEY AUTOINCREMENT,
                systemID INTEGER NOT NULL,
                cheatDeviceName TEXT NOT NULL,
                cheatDeviceBrandName TEXT,
                cheatDeviceFormat TEXT,
                FOREIGN KEY (systemID)
                    REFERENCES SYSTEMS (systemID)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
            )
        """
        self.cursor.execute(query)
        query = """
            CREATE TABLE CHEAT_CATEGORIES (
                cheatCategoryID INTEGER
                    PRIMARY KEY AUTOINCREMENT,
                cheatCategory TEXT NOT NULL,
                cheatCategoryDescription TEXT
            )
        """
        self.cursor.execute(query)
        query = """
            CREATE TABLE CHEATS (
                cheatID INTEGER
                    PRIMARY KEY AUTOINCREMENT,
                romID INTEGER NOT NULL,
                cheatName TEXT NOT NULL,
                cheatActivation TEXT,
                cheatDescription TEXT,
                cheatSideEffect TEXT,
                cheatFolderName TEXT,
                cheatCategoryID INTEGER NOT NULL,
                cheatCode TEXT NOT NULL,
                cheatDeviceID INTEGER NOT NULL,
                cheatCredit,
                FOREIGN KEY (romID)
                    REFERENCES ROMs (romID)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
                FOREIGN KEY (cheatCategoryID)
                    REFERENCES CHEAT_CATEGORIES (cheatCategoryID)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
                FOREIGN KEY (cheatDeviceID)
                    REFERENCES CHEAT_DEVICES (cheatDeviceID)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
            )
        """
        self.cursor.execute(query)

        # Insert data
        query = """
            INSERT INTO CHEAT_DEVICES (cheatDeviceID, systemID, cheatDeviceName, cheatDeviceBrandName, cheatDeviceFormat)
            VALUES (:cheatdevid, :sysid, :cheatdevname, :cheatdevbrand, :cheatdevfmt)
        """
        self.cursor.executemany(query, cheat_devices)

        query = """
            INSERT INTO CHEAT_CATEGORIES (cheatCategoryID, cheatCategory, cheatCategoryDescription)
            VALUES (:cheatcategoryid, :cheatcategory, :cheatcategorydesc)
        """
        self.cursor.executemany(query, cheat_categories)

        query = """
            INSERT INTO CHEATS (romID, cheatName, cheatActivation, cheatDescription, cheatSideEffect, cheatFolderName, cheatCategoryID, cheatCode, cheatDeviceID, cheatCredit)
            VALUES (:romid, :cheatname, :cheatactiv, :cheatdesc, :cheatside, :cheatfolder, :cheatcategory, :cheatcode, :cheatdevice, :cheatcred)
        """
        self.cursor.executemany(query, allcheats)

# Tree diagram that shows the relation of foreign keys that must be updated
# If you 'organize' any tables that have branches, you must parse those tables too, otherwise the keys won't be updated
# .
# ├── systemID
# │   ├── romID
# │   │   ├── cheatID
# │   │   └── releaseID
# │   └── cheatDeviceID
# │       └── cheatID
# ├── regionID
# │   ├── romID
# │   │   ├── cheatID
# │   │   └── releaseID
# │   └── releaseID
# └── cheatCategoryID
#     └── cheatID

p = Parser()

try:
    organize_all = True
    p.parse_systems(organize=False or organize_all)
    p.parse_regions(organize=False or organize_all)
    p.parse_roms(organize=False or organize_all)
    p.parse_releases(organize=False or organize_all)
    p.parse_cheats(organize=False or organize_all) # handles cheats, cheat_categories, and cheat_devices
except Exception as err:
    print("Error detected, rolling back changes.")
    p.conn.rollback()
    raise(err)

p.conn.commit()
print("Changes committed. Now starting cleanup.")
p.cursor.execute("VACUUM")
p.conn.commit()
