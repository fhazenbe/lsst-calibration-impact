
#!/usr/bin/env python 


import os
import os.path 
import sys

import numpy as np
import matplotlib.pyplot as plt

from croaks import NTuple
from saunerie import psf, snsim, salt2
import time


model_components = None
def init_lcmodel(bands, filename='salt2.npz'):
    """
    Utility function to load a SALT2 light curve model. 
    The model components are cached. 

    This should be a function of the snsim module.
    """
    global model_components
    if model_components is None:
        print 'we have to reload model_components'
        if filename is None:
            model_components = salt2.ModelComponents.load_from_saltpath()
        else:
            model_components = salt2.ModelComponents(filename)
    fs = salt2.load_filters(np.unique(bands))
    lcmodel = snsim.SALT2LcModel(fs, model_components)
    return lcmodel

def create_log(survey_type, mjd_min=59884., CARD=None):
    if CARD is None:
        CARD = CARDS[survey_type]
    bands = CARD['bands']
    texp = CARD['texp']
    sky = CARD['sky']
    seeing = CARD['seeing']
    duration = CARD['duration']
    cadences = CARD['cadences']
    m5sig = CARD['m5sig']
    mjd_max = mjd_min + duration
    log_example = NTuple.fromtxt('Observations_DD_290_LSSTPG.txt')
    dt = log_example.dtype
    dates, _bands, _seeing, _sky, _texp, _m5sig = [], [], [], [], [], []
    for i, band in enumerate(bands):
        date = np.arange(mjd_min, mjd_max, cadences[i])
        dates += [np.arange(mjd_min, mjd_max, cadences[i])]
        ld = len(date)
        _bands += [np.tile(np.array(bands[i]), ld)]
        _seeing += [np.tile(np.array(seeing[i]), ld)]
        _sky += [np.tile(np.array(sky[i]), ld)]
        _texp += [np.tile(np.array(texp[i]), ld)]
        _m5sig += [np.tile(np.array(m5sig[i]), ld)]
    dates = np.hstack(dates)
    log = np.zeros(len(dates), dtype=dt)
    log['mjd'] = dates
    log['band'] = np.hstack(_bands)
    log['seeing'] = np.hstack(_seeing)
    log['sky'] = np.hstack(_sky)
    log['kAtm'] = np.mean(log_example['kAtm'])
    log['airmass'] = 1
    log['exptime'] = np.hstack(_texp)
    log['m5sigmadepth'] = np.hstack(_m5sig)
    return log.view(NTuple)
    
def plot_of_interest(lcs, stype='unknown-survey-type', record=False):
    z, sigma_c, t0, x1 = [], [], [], []
    for lc in lcs:
        C = lc.covmat()
        z += [lc.sn['z']]
        sigma_c += [np.sqrt(C[2,2])]
        t0 += [np.sqrt(C[1,1])]
        x1 += [np.sqrt(C[3,3])]
    fig, ax = plt.subplots(3, 1, sharex=True)
    ax[0].semilogy(z, sigma_c, '+')
    ax[0].axhline(0.03, lw=3, color='r')
    ax[1].semilogy(z, t0, '+')
    ax[2].semilogy(z, x1, '+')
    for i in range(3):
        for tick in ax[i].yaxis.get_major_ticks():
            tick.label.set_fontsize(20)
    ax[0].set_ylabel('$\sigma_c$', fontsize=25)
    ax[1].set_ylabel('$\sigma_{t_0}$', fontsize=24)
    ax[2].set_ylabel('$\sigma_{X_1}$', fontsize=24)
    plt.xticks(fontsize=22)

    plt.xlabel('$z$', fontsize=23)
    [ax[i].grid() for i in range(3)]

def create_survey(survey_type, mjd_min=59884., color=True, n=1, CARD=None, zrange=(0.05, 1), graph=False, record=False):
    log = [snsim.OpSimObsLog(create_log(survey_type, mjd_min)) for i in range(n)]
    lcmodel = init_lcmodel(log[0].band)
    #r = log.split()
    lc = []
    if CARD is None:
        CARD = CARDS[survey_type]
    for i in range(n):
        print ('Creating %s survey (# %d over %d seasons) --- ' + time.ctime()) % (survey_type, i+1, n)
        s = snsim.SnSurveyMC(obslog=log[i], filename='lsst_survey.conf')
        s.survey_area = CARD['field']
        s.zrange = zrange
        sne = s.generate_sample(account_for_edges=True)
        sne.sort(order='z')
        # sne['X1'] = 0
        if color is False:
            sne['Color'] = 0
        lc += s.generate_lightcurves(sne, lcmodel, fit=1)
    if graph:
        plot_of_interest(lc, survey_type, record)
    return lc

"""
Examples of LSST SN survey layers, that you can use or be inpired by
to create your own with your specific median observing conditions in
each band
"""
CARDS = {'deep_ideal' : {'bands' : np.array(['LSSTPG::'+band for band in ['r', 'i', 'z', 'y']]), 
                         'texp' : np.array([1200, 1800,  1800, 1800]), 
                         'sky' : np.array([21.19, 20.46, 19.60, 18.61]), 
                         'seeing' : np.array([0.83, 0.80, 0.78, 0.76]), 
                         'm5sig' : np.array([26.43, 26.16, 25.56, 24.68]), 
                         'cadences' : np.array([3, 3, 3, 3]),
                         'field' : 100.,
                         'duration' : 180.},
         'deep_opsim' : {'bands' : np.array(['LSSTPG::'+band for band in ['r', 'i', 'z', 'y']]), 
                         'texp' : np.array([600, 600,  720, 600]), 
                         'sky' : np.array([20.92, 19.89, 19.06, 17.30]), 
                         'seeing' : np.array([0.98, 0.92, 0.89, 0.86]), 
                         'm5sig' : np.array([25.74, 25.12, 24.65, 23.29]),
                         'cadences' : np.array([8, 8, 8, 8]),
                         'field' : 100.,
                         'duration' : 135},
         'deep_ideal_court' : {'bands' : np.array(['LSSTPG::'+band for band in ['r', 'i', 'z', 'y']]), 
                               'texp' : np.array([1200, 1800,  1800, 1800]), 
                               'sky' : np.array([21.19, 20.46, 19.60, 18.61]), 
                               'seeing' : np.array([0.83, 0.80, 0.78, 0.76]), 
                               'm5sig' : np.array([26.43, 26.16, 25.56, 24.68]), 
                               'cadences' : np.array([3, 3, 3, 3]),
                               'field' : 100.,
                               'duration' : 135.},
         'wide' : {'bands' : np.array(['LSSTPG::'+band for band in ['g', 'r', 'i', 'z']]), 
                   'texp' : np.array([30, 30, 30, 30]), 
                   'sky' : np.array([22.23, 21.19, 20.46, 19.60]), 
                   'seeing' : np.array([0.87, 0.83, 0.80, 0.78]), 
                   'm5sig' : np.array([24.83, 24.35, 23.88, 23.30]),
                   'cadences' : np.array([6, 3, 3, 4]),
                   'field' : 6500.,
                   'duration' : 180.}
}
