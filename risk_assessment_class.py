# -*- coding: utf-8 -*-
"""
Created on Mon Feb  1 05:54:20 2021

@author: 44797
"""
import subprocess
import pickle
from scipy.stats import beta, linregress, norm
import matplotlib.pyplot as plt
from sklearn import preprocessing
import pandas as pd
import numpy as np

class RiskAssessment():
    def __init__(self, company_value, ratings, 
                 financials, max_, lgd_var_data, money_lent, money_commited,
                 liability_weight_range=(0.1,0.2), 
                 ave_lgd=0.22):
        self.company_value = company_value
        # self.exposure = exposure
        self.ratings = ratings
        self.financials = pd.read_csv(financials)
        self.max_ = max_
        self.ave_lgd = ave_lgd
        self.lgd_var = np.std(lgd_var_data)
        self.min_l_weight, self.max_l_weight = liability_weight_range
        self.lent = money_lent
        self.commited = money_commited
        self.ead = None
        self.expected_return = None
        self.volatility = None
        self.default_point = None
        self.pd = None
        self.lgd = None
        self.total_assets = None
        
      
    def calc_expected_return_volatility(self):
        company_financials = self.financials
        company_financials = company_financials.drop(['Attributes'], axis=1)
        total_assets = company_financials.loc['Total Current Assets']
        total_assets = [int(x) for x in total_assets.iloc[0].name][::-1]
        normalised_total_assets = preprocessing.normalize(np.array(total_assets).reshape(1,7))
        x = np.linspace(1, len(total_assets), len(total_assets))
        growth, _, _, _, _, = linregress(x, np.array(normalised_total_assets).reshape(7,))
        self.expected_return = growth
        self.volatility = np.std(normalised_total_assets)
        self.total_assets = total_assets[0]
        
        return self.expected_return, self.volatility
    
    def exposure_at_default(self, a=2, b=5):
        loc = min(self.ratings)
        scale = max(self.ratings) - loc
        credit_score = beta.rvs(a, b, loc=loc, scale=scale)
        self.ead = (self.lent + (self.commited * credit_score)) - self.total_assets
        # print('{:,}'.format(self.ead))
        
        return self.ead
    
    def calc_default_point(self):
        company_financials = self.financials
        short_term_liability = company_financials.loc['Total Current Liabilities']
        short_term_liability = int(short_term_liability.iloc[0].name[0])
        long_term_liability = company_financials.loc['Total Long Term Finance']
        long_term_liability = int(long_term_liability.iloc[0].name[0])
        default_weighting = np.random.uniform(self.min_l_weight, 
                                              self.max_l_weight, 1)[0]
        self.default_point = short_term_liability + (long_term_liability * default_weighting)
        
        return self.default_point
    
    def probability_of_default(self, t=1):
        numerator = np.log(self.company_value) + (self.expected_return - (self.volatility**2/2)) * t - np.log(self.default_point)
        denominator = self.volatility * t
        dd = numerator / denominator
        self.pd = norm.cdf(-dd)
        
        return norm.cdf(-dd)
    
    def loss_given_default(self):
        l = self.ave_lgd/self.max_
        r = (self.ave_lgd * (self.max_ - self.ave_lgd))/(self.max_ * self.lgd_var**2)
        alpha = l * r - 1
        beta = alpha * ((self.max_/self.ave_lgd) - 1)
    
        mean_recovery = alpha / (alpha + beta)
        self.lgd = 1 - mean_recovery
        
        return self.lgd
    
    def expected_loss(self):
        # print(self.ead, self.pd, self.lgd)
        
        el = self.ead * self.pd * self.lgd
        
        return el


if __name__ == '__main__':

    risk_ass = RiskAssessment(43.1 * 1000000, [0.69,0.73,0.71,0.65,0.52,0.48,0.44], 'company_financials.csv', 
                            1, [35,32,27,22,17,19,19,30,30,19,19,22,21,19,21,23], 40000000, 10000000)

    risk_metrics = {}
    risk_metrics['Expected Growth'] = '{}%'.format(round(risk_ass.calc_expected_return_volatility()[0]*100, 2))
    risk_metrics['Exposure'] = '£{:,.2f}'.format(risk_ass.exposure_at_default())
    risk_metrics['Point of Default'] = '£{:,}'.format(round(risk_ass.calc_default_point(), 2))
    risk_metrics['Probability of Default'] = round(risk_ass.probability_of_default(), 2)
    risk_metrics['Loss Given Default'] = '{}%'.format(round(risk_ass.loss_given_default()*100, 2))
    risk_metrics['Expected Loss'] = '£{:,.2f}'.format(risk_ass.expected_loss())

    print('With £{:,.2f} exposure, expected losses are £{:,.2f}.'.format(risk_ass.exposure_at_default(), risk_ass.expected_loss()))

    with open('risk_metrics.pickle', 'wb') as fp:
        pickle.dump(risk_metrics, fp, protocol=pickle.HIGHEST_PROTOCOL)