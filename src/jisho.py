import os
import re
from pykakasi import kakasi

class Jisho():
    def __init__(self, dict:str, index:str, index2:str):
        self.lines = open(dict, 'r', encoding='utf-8').readlines()
        self.index = open(index, 'r', encoding='utf-8').read().splitlines()
        self.pronindex = open(index2, 'r', encoding='utf-8').read().splitlines()
        self.kks = kakasi()
    
    def lookUp(self, word:str):
        location = -1
        try:
            location = self.index.index(word)
            location = eval(self.index[location+1])

        except ValueError:
            try:
                location = self.pronindex.index(self.kks.convert(word)[0]['hira'])
                location = eval(self.pronindex[location+1])
            except ValueError:
                return f'{word} not found.'
        s = ''
        while(self.lines[location][0] != '}'):
            s += self.lines[location]
            location+=1
        return s.lstrip('{')


# jisho = Jisho('./JA-ZHdict.dat', './JA-ZHdictindex.dat', './JA-ZHdictpronindex.dat')
# print(jisho.lookUp('大根'))
# print(jisho.lookUp('カタカナ'))