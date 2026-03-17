# Standard Library
import requests

# Local Modules
from Configuration import (RECRUITMENT_DRIVE_URL, CHAPTER_NAME)

class Recruitment_Drive_Processor:
    
    def __init__(self):
        response = requests.get(RECRUITMENT_DRIVE_URL)

        self.absolute_increase_array = [['#', 'Chapter', 'Members']]
        self.relative_increase_array = [['#', 'Chapter', 'Increase']]
        self.chapter_absolute_increase = None
        self.chapter_relative_increase = None
        self.errors = None

        if response.status_code != 200:
            self.errors = response.status_code
            return
        
        payload = response.json()

        absolute_increase = payload['data']['chapters']['dsa']
        relative_increase = payload['data']['chapters']['dsa_increase']

        closure = -1
        counter = 1
        for chapter in absolute_increase:
            chapter_name = chapter['chapter']
            value = str(chapter['referrals'])

            if chapter['chapter'] == CHAPTER_NAME:
                chapter_name = chapter_name.upper()
                closure = counter + 2
                self.chapter_absolute_increase = value

            self.absolute_increase_array.append([str(counter), chapter_name, value])

            if counter == closure:
                break

            counter += 1

        closure = -1
        counter = 1
        for chapter in relative_increase:
            chapter_name = chapter['chapter']
            value = '{0:.2f}'.format(chapter['relative_increase']) + '%'

            if chapter['chapter'] == 'Sonoma County':
                chapter_name = chapter_name.upper()
                closure = counter + 5
                self.chapter_relative_increase = value

            self.relative_increase_array.append([str(counter), chapter_name, value])
            if counter == closure:
                break

            counter += 1




















        self.successes = {}
        self.failures = {}