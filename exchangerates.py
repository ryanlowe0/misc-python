#!/usr/local/bin/python

import re
import sys
from urllib import urlopen
from plant.dbengine import transactional
from plant.smartdate import Date
from plant.resources import res
from plant.model import ExchangeRate


class ExchangeRates(object):
    def __init__(self):
        from attributes import Attributes
        self.currencies = Attributes('Currency')

    @transactional
    def updateToday(self, session, currency_ids=[1, 2, 3]):
        xrates = urlopen('http://www.x-rates.com/calculator.html').read()
        data = '\s*=\s*new\s+Array\s*\(([\w",.\s]+)\)'
        currency_list = list(eval(re.compile('currency' + data)
                                  .search(xrates)
                                  .groups()[0]))
        rate_list = list(eval(re.compile('rate' + data)
                              .search(xrates)
                              .groups()[0]))
        for id in currency_ids:
            cur = self.currencies.getCode(id)
            rate = float(rate_list[currency_list.index(cur)])
            exchange_rate = ExchangeRate(rate_date=Date(),
                                         currency_id=id,
                                         rate=rate)
            session.merge(exchange_rate)
                          
    @transactional
    def updateLast120(self, session, currency_ids=[1, 2, 3]):
        ' scrapes rates for last 120 days from www.x-rates.com '

        from sqlalchemy.sql import update
        
        extractor = re.compile(
            '<tr[^>]*>\n'
            '<td><font face="Verdana" size="-1">([\d-]+)</font></td>\n'
            '<td><font face="Verdana" size="-1">.*?</font></td>\n'
            '<td><font face="Verdana" size="-1">([\d.]+)</font></td>\n'
            '<td><font face="Verdana" size="-1">.*?</font></td>\n'
            '</tr>')

        for id in currency_ids:
            cur = self.currencies.getCode(id)
            last120 = urlopen('http://www.x-rates.com/d/%s/USD/data120.html' %
                              cur).read()
            for date, rate in extractor.findall(last120):
                exchange_rate = ExchangeRate(rate_date=date, 
                                             currency_id=id, 
                                             rate=rate)
                session.merge(exchange_rate)

    @transactional
    def getToday(self, session):
        self.updateToday(session)
        return session.query(ExchangeRate).filter_by(rate_date=Date()).all()

       
if __name__ == '__main__':
    res.load()
    #ExchangeRates().updateToday()
    print ExchangeRates().getToday()
    #ExchangeRates().updateLast120()



