import sys
import numpy as np
from copy import copy
from scipy import stats
from astropy.io import fits as pyfits
from matplotlib import pyplot as plt
import kepio, kepmsg, kepkey, kepstat, kepfit

def kepfold(infile,outfile,period,phasezero,bindata,binmethod,threshold,niter,nbins,
            rejqual,plottype,plotlab,clobber,verbose,logfile,status,cmdLine=False):

# startup parameters

    status = 0
    labelsize = 32; ticksize = 18; xsize = 18; ysize = 10
    lcolor = '#0000ff'; lwidth = 2.0; fcolor = '#ffff00'; falpha = 0.2

# log the call

    hashline = '----------------------------------------------------------------------------'
    kepmsg.log(logfile,hashline,verbose)
    call = 'KEPFOLD -- '
    call += 'infile='+infile+' '
    call += 'outfile='+outfile+' '
    call += 'period='+str(period)+' '
    call += 'phasezero='+str(phasezero)+' '
    binit = 'n'
    if (bindata): binit = 'y'
    call += 'bindata='+binit+' '
    call += 'binmethod='+binmethod+' '
    call += 'threshold='+str(threshold)+' '
    call += 'niter='+str(niter)+' '
    call += 'nbins='+str(nbins)+' '
    qflag = 'n'
    if (rejqual): qflag = 'y'
    call += 'rejqual='+qflag+ ' '
    call += 'plottype='+plottype+ ' '
    call += 'plotlab='+plotlab+ ' '
    overwrite = 'n'
    if (clobber): overwrite = 'y'
    call += 'clobber='+overwrite+ ' '
    chatter = 'n'
    if (verbose): chatter = 'y'
    call += 'verbose='+chatter+' '
    call += 'logfile='+logfile
    kepmsg.log(logfile,call+'\n',verbose)

# start time

    kepmsg.clock('KEPFOLD started at',logfile,verbose)

# test log file

    logfile = kepmsg.test(logfile)

# clobber output file

    if clobber: status = kepio.clobber(outfile,logfile,verbose)
    if kepio.fileexists(outfile):
        message = 'ERROR -- KEPFOLD: ' + outfile + ' exists. Use --clobber'
        status = kepmsg.err(logfile,message,verbose)

# open input file

    if status == 0:
        instr, status = kepio.openfits(infile,'readonly',logfile,verbose)
    if status == 0:
        tstart, tstop, bjdref, cadence, status = kepio.timekeys(instr,infile,logfile,verbose,status)
    if status == 0:
        try:
            work = instr[0].header['FILEVER']
            cadenom = 1.0
        except:
            cadenom = cadence

# fudge non-compliant FITS keywords with no values

    if status == 0:
        instr = kepkey.emptykeys(instr,file,logfile,verbose)

# input data

    if status == 0:
        table = instr[1].data
        incards = instr[1].header.cards
        try:
            sap = instr[1].data.field('SAP_FLUX')
        except:
            try:
                sap = instr[1].data.field('ap_raw_flux')
            except:
                sap = np.zeros(len(table.field(0)))
        try:
            saperr = instr[1].data.field('SAP_FLUX_ERR')
        except:
            try:
                saperr = instr[1].data.field('ap_raw_err')
            except:
                saperr = np.zeros(len(table.field(0)))
        try:
            pdc = instr[1].data.field('PDCSAP_FLUX')
        except:
            try:
                pdc = instr[1].data.field('ap_corr_flux')
            except:
                pdc = np.zeros(len(table.field(0)))
        try:
            pdcerr = instr[1].data.field('PDCSAP_FLUX_ERR')
        except:
            try:
                pdcerr = instr[1].data.field('ap_corr_err')
            except:
                pdcerr = np.zeros(len(table.field(0)))
        try:
            cbv = instr[1].data.field('CBVSAP_FLUX')
        except:
            cbv = np.zeros(len(table.field(0)))
            if 'cbv' in plottype:
                txt = 'ERROR -- KEPFOLD: CBVSAP_FLUX column is not populated. Use kepcotrend'
                status = kepmsg.err(logfile,txt,verbose)
        try:
            det = instr[1].data.field('DETSAP_FLUX')
        except:
            det = np.zeros(len(table.field(0)))
            if 'det' in plottype:
                txt = 'ERROR -- KEPFOLD: DETSAP_FLUX column is not populated. Use kepflatten'
                status = kepmsg.err(logfile,txt,verbose)
        try:
            deterr = instr[1].data.field('DETSAP_FLUX_ERR')
        except:
            deterr = np.zeros(len(table.field(0)))
            if 'det' in plottype:
                txt = 'ERROR -- KEPFOLD: DETSAP_FLUX_ERR column is not populated. Use kepflatten'
                status = kepmsg.err(logfile,txt,verbose)
        try:
            quality = instr[1].data.field('SAP_QUALITY')
        except:
            quality = np.zeros(len(table.field(0)))
            if qualflag:
                txt = 'WARNING -- KEPFOLD: Cannot find a QUALITY data column'
                kepmsg.warn(logfile,txt)
    if status == 0:
        barytime, status = kepio.readtimecol(infile,table,logfile,verbose)
        barytime1 = copy(barytime)


# filter out NaNs and quality > 0

    work1 = []; work2 = []; work3 = []; work4 = []; work5 = []; work6 = []; work8 = []; work9 = []
    if status == 0:
        if 'sap' in plottype:
            datacol = copy(sap)
            errcol = copy(saperr)
        if 'pdc' in plottype:
            datacol = copy(pdc)
            errcol = copy(pdcerr)
        if 'cbv' in plottype:
            datacol = copy(cbv)
            errcol = copy(saperr)
        if 'det' in plottype:
            datacol = copy(det)
            errcol = copy(deterr)
        for i in range(len(barytime)):
            if (np.isfinite(barytime[i]) and
                np.isfinite(datacol[i]) and datacol[i] != 0.0 and
                np.isfinite(errcol[i]) and errcol[i] > 0.0):
                if rejqual and quality[i] == 0:
                    work1.append(barytime[i])
                    work2.append(sap[i])
                    work3.append(saperr[i])
                    work4.append(pdc[i])
                    work5.append(pdcerr[i])
                    work6.append(cbv[i])
                    work8.append(det[i])
                    work9.append(deterr[i])
                elif not rejqual:
                    work1.append(barytime[i])
                    work2.append(sap[i])
                    work3.append(saperr[i])
                    work4.append(pdc[i])
                    work5.append(pdcerr[i])
                    work6.append(cbv[i])
                    work8.append(det[i])
                    work9.append(deterr[i])
        barytime = np.array(work1,dtype='float64')
        sap = np.array(work2,dtype='float32') / cadenom
        saperr = np.array(work3,dtype='float32') / cadenom
        pdc = np.array(work4,dtype='float32') / cadenom
        pdcerr = np.array(work5,dtype='float32') / cadenom
        cbv = np.array(work6,dtype='float32') / cadenom
        det = np.array(work8,dtype='float32') / cadenom
        deterr = np.array(work9,dtype='float32') / cadenom

# calculate phase

    if status == 0:
        if phasezero < bjdref:
            phasezero += bjdref
        date1 = (barytime1 + bjdref - phasezero)
        phase1 = (date1 / period) - np.floor(date1/period)
        date2 = (barytime + bjdref - phasezero)
        phase2 = (date2 / period) - np.floor(date2/period)
        phase2 = np.array(phase2,'float32')

# sort phases

    if status == 0:
        ptuple = []
        phase3 = [];
        sap3 = []; saperr3 = []
        pdc3 = []; pdcerr3 = []
        cbv3 = []; cbverr3 = []
        det3 = []; deterr3 = []
        for i in range(len(phase2)):
            ptuple.append([phase2[i], sap[i], saperr[i], pdc[i], pdcerr[i], cbv[i], saperr[i], det[i], deterr[i]])
        phsort = sorted(ptuple,key=lambda ph: ph[0])
        for i in range(len(phsort)):
            phase3.append(phsort[i][0])
            sap3.append(phsort[i][1])
            saperr3.append(phsort[i][2])
            pdc3.append(phsort[i][3])
            pdcerr3.append(phsort[i][4])
            cbv3.append(phsort[i][5])
            cbverr3.append(phsort[i][6])
            det3.append(phsort[i][7])
            deterr3.append(phsort[i][8])
        phase3 = np.array(phase3,'float32')
        sap3 = np.array(sap3,'float32')
        saperr3 = np.array(saperr3,'float32')
        pdc3 = np.array(pdc3,'float32')
        pdcerr3 = np.array(pdcerr3,'float32')
        cbv3 = np.array(cbv3,'float32')
        cbverr3 = np.array(cbverr3,'float32')
        det3 = np.array(det3,'float32')
        deterr3 = np.array(deterr3,'float32')

# bin phases

    if status == 0 and bindata:
        work1 = np.array([sap3[0]],'float32')
        work2 = np.array([saperr3[0]],'float32')
        work3 = np.array([pdc3[0]],'float32')
        work4 = np.array([pdcerr3[0]],'float32')
        work5 = np.array([cbv3[0]],'float32')
        work6 = np.array([cbverr3[0]],'float32')
        work7 = np.array([det3[0]],'float32')
        work8 = np.array([deterr3[0]],'float32')
        phase4 = np.array([],'float32')
        sap4 = np.array([],'float32')
        saperr4 = np.array([],'float32')
        pdc4 = np.array([],'float32')
        pdcerr4 = np.array([],'float32')
        cbv4 = np.array([],'float32')
        cbverr4 = np.array([],'float32')
        det4 = np.array([],'float32')
        deterr4 = np.array([],'float32')
        dt = 1.0 / nbins
        nb = 0.0
        rng = np.append(phase3,phase3[0]+1.0)
        for i in range(len(rng)):
            if rng[i] < nb * dt or rng[i] >= (nb + 1.0) * dt:
                if len(work1) > 0:
                    phase4 = np.append(phase4,(nb + 0.5) * dt)
                    if (binmethod == 'mean'):
                        sap4 = np.append(sap4,kepstat.mean(work1))
                        saperr4 = np.append(saperr4,kepstat.mean_err(work2))
                        pdc4 = np.append(pdc4,kepstat.mean(work3))
                        pdcerr4 = np.append(pdcerr4,kepstat.mean_err(work4))
                        cbv4 = np.append(cbv4,kepstat.mean(work5))
                        cbverr4 = np.append(cbverr4,kepstat.mean_err(work6))
                        det4 = np.append(det4,kepstat.mean(work7))
                        deterr4 = np.append(deterr4,kepstat.mean_err(work8))
                    elif (binmethod == 'median'):
                        sap4 = np.append(sap4,kepstat.median(work1,logfile))
                        saperr4 = np.append(saperr4,kepstat.mean_err(work2))
                        pdc4 = np.append(pdc4,kepstat.median(work3,logfile))
                        pdcerr4 = np.append(pdcerr4,kepstat.mean_err(work4))
                        cbv4 = np.append(cbv4,kepstat.median(work5,logfile))
                        cbverr4 = np.append(cbverr4,kepstat.mean_err(work6))
                        det4 = np.append(det4,kepstat.median(work7,logfile))
                        deterr4 = np.append(deterr4,kepstat.mean_err(work8))
                    else:
                        coeffs, errors, covar, iiter, sigma, chi2, dof, fit, plotx, ploty, status = \
                            kepfit.lsqclip('poly0',[nanmean(work1)],arange(0.0,float(len(work1)),1.0),work1,work2,
                                           threshold,threshold,niter,logfile,False)
                        sap4 = np.append(sap4,coeffs[0])
                        saperr4 = np.append(saperr4,kepstat.mean_err(work2))
                        coeffs, errors, covar, iiter, sigma, chi2, dof, fit, plotx, ploty, status = \
                            kepfit.lsqclip('poly0',[nanmean(work3)],arange(0.0,float(len(work3)),1.0),work3,work4,
                                           threshold,threshold,niter,logfile,False)
                        pdc4 = np.append(pdc4,coeffs[0])
                        pdcerr4 = np.append(pdcerr4,kepstat.mean_err(work4))
                        coeffs, errors, covar, iiter, sigma, chi2, dof, fit, plotx, ploty, status = \
                            kepfit.lsqclip('poly0',[nanmean(work5)],arange(0.0,float(len(work5)),1.0),work5,work6,
                                           threshold,threshold,niter,logfile,False)
                        cbv4 = np.append(cbv4,coeffs[0])
                        cbverr4 = np.append(cbverr4,kepstat.mean_err(work6))
                        coeffs, errors, covar, iiter, sigma, chi2, dof, fit, plotx, ploty, status = \
                            kepfit.lsqclip('poly0',[nanmean(work7)],arange(0.0,float(len(work7)),1.0),work7,work8,
                                           threshold,threshold,niter,logfile,False)
                        det4 = np.append(det4,coeffs[0])
                        deterr4 = np.append(deterr4,kepstat.mean_err(work8))
                work1 = np.array([],'float32')
                work2 = np.array([],'float32')
                work3 = np.array([],'float32')
                work4 = np.array([],'float32')
                work5 = np.array([],'float32')
                work6 = np.array([],'float32')
                work7 = np.array([],'float32')
                work8 = np.array([],'float32')
                nb += 1.0
            else:
                work1 = np.append(work1,sap3[i])
                work2 = np.append(work2,saperr3[i])
                work3 = np.append(work3,pdc3[i])
                work4 = np.append(work4,pdcerr3[i])
                work5 = np.append(work5,cbv3[i])
                work6 = np.append(work6,cbverr3[i])
                work7 = np.append(work7,det3[i])
                work8 = np.append(work8,deterr3[i])

# update HDU1 for output file

    if status == 0:

        cols = (instr[1].columns + pyfits.ColDefs([pyfits.Column(name='PHASE',format='E',array=phase1)]))
        instr[1] = pyfits.BinTableHDU.from_columns(cols)
        instr[1].header.cards['TTYPE'+str(len(instr[1].columns))].comment = 'column title: phase'
        instr[1].header.cards['TFORM'+str(len(instr[1].columns))].comment = 'data type: float32'
        for i in range(len(incards)):
            if incards[i].keyword not in instr[1].header.keys():
                instr[1].header[incards[i].keyword] = (incards[i].value, incards[i].comment)
            else:
                instr[1].header.cards[incards[i].keyword].comment = incards[i].comment
        instr[1].header['PERIOD'] = (period,'period defining the phase [d]')
        instr[1].header['BJD0'] = (phasezero,'time of phase zero [BJD]')

# write new phased data extension for output file

    if status == 0 and bindata:
        col1 = pyfits.Column(name='PHASE',format='E',array=phase4)
        col2 = pyfits.Column(name='SAP_FLUX',format='E',unit='e/s',array=sap4/cadenom)
        col3 = pyfits.Column(name='SAP_FLUX_ERR',format='E',unit='e/s',array=saperr4/cadenom)
        col4 = pyfits.Column(name='PDC_FLUX',format='E',unit='e/s',array=pdc4/cadenom)
        col5 = pyfits.Column(name='PDC_FLUX_ERR',format='E',unit='e/s',array=pdcerr4/cadenom)
        col6 = pyfits.Column(name='CBV_FLUX',format='E',unit='e/s',array=cbv4/cadenom)
        col7 = pyfits.Column(name='DET_FLUX',format='E',array=det4/cadenom)
        col8 = pyfits.Column(name='DET_FLUX_ERR',format='E',array=deterr4/cadenom)
        cols = pyfits.ColDefs([col1,col2,col3,col4,col5,col6,col7,col8])
        instr.append(pyfits.BinTableHDU.from_columns(cols))
        instr[-1].header.cards['TTYPE1'].comment = 'column title: phase'
        instr[-1].header.cards['TTYPE2'].comment = 'column title: simple aperture photometry'
        instr[-1].header.cards['TTYPE3'].comment = 'column title: SAP 1-sigma error'
        instr[-1].header.cards['TTYPE4'].comment = 'column title: pipeline conditioned photometry'
        instr[-1].header.cards['TTYPE5'].comment = 'column title: PDC 1-sigma error'
        instr[-1].header.cards['TTYPE6'].comment = 'column title: cotrended basis vector photometry'
        instr[-1].header.cards['TTYPE7'].comment = 'column title: Detrended aperture photometry'
        instr[-1].header.cards['TTYPE8'].comment = 'column title: DET 1-sigma error'
        instr[-1].header.cards['TFORM1'].comment = 'column type: float32'
        instr[-1].header.cards['TFORM2'].comment = 'column type: float32'
        instr[-1].header.cards['TFORM3'].comment = 'column type: float32'
        instr[-1].header.cards['TFORM4'].comment = 'column type: float32'
        instr[-1].header.cards['TFORM5'].comment = 'column type: float32'
        instr[-1].header.cards['TFORM6'].comment = 'column type: float32'
        instr[-1].header.cards['TFORM7'].comment = 'column type: float32'
        instr[-1].header.cards['TFORM8'].comment = 'column type: float32'
        instr[-1].header.cards['TUNIT2'].comment = 'column units: electrons per second'
        instr[-1].header.cards['TUNIT3'].comment = 'column units: electrons per second'
        instr[-1].header.cards['TUNIT4'].comment = 'column units: electrons per second'
        instr[-1].header.cards['TUNIT5'].comment = 'column units: electrons per second'
        instr[-1].header.cards['TUNIT6'].comment = 'column units: electrons per second'
        instr[-1].header['EXTNAME']    = ('FOLDED','extension name')
        instr[-1].header['PERIOD']     = (period,'period defining the phase [d]')
        instr[-1].header['BJD0']       = (phasezero,'time of phase zero [BJD]')
        instr[-1].header['BINMETHD']   = (binmethod,'phase binning method')
        if binmethod =='sigclip':
            instr[-1].header['THRSHOLD'] = (threshold,'sigma-clipping threshold [sigma]')
            instr[-1].header['NITER']    = (niter,'max number of sigma-clipping iterations')

# history keyword in output file

    if status == 0:
        status = kepkey.history(call,instr[0],outfile,logfile,verbose)
        instr.writeto(outfile)

# clean up x-axis unit

    if status == 0:
        ptime1 = np.array([],'float32')
        ptime2 = np.array([],'float32')
        pout1 = np.array([],'float32')
        pout2 = np.array([],'float32')
        if bindata:
            work = sap4
            if plottype == 'pdc':
                work = pdc4
            if plottype == 'cbv':
                work = cbv4
            if plottype == 'det':
                work = det4
            for i in range(len(phase4)):
                if (phase4[i] > 0.5):
                    ptime2 = np.append(ptime2,phase4[i] - 1.0)
                    pout2 = np.append(pout2,work[i])
            ptime2 = np.append(ptime2,phase4)
            pout2 = np.append(pout2,work)
            for i in range(len(phase4)):
                if (phase4[i] <= 0.5):
                    ptime2 = np.append(ptime2,phase4[i] + 1.0)
                    pout2 = np.append(pout2,work[i])
        work = sap3
        if plottype == 'pdc':
            work = pdc3
        if plottype == 'cbv':
            work = cbv3
        if plottype == 'det':
            work = det3
        for i in range(len(phase3)):
            if (phase3[i] > 0.5):
                ptime1 = np.append(ptime1,phase3[i] - 1.0)
                pout1 = np.append(pout1,work[i])
        ptime1 = np.append(ptime1,phase3)
        pout1 = np.append(pout1,work)
        for i in range(len(phase3)):
            if (phase3[i] <= 0.5):
                ptime1 = np.append(ptime1,phase3[i] + 1.0)
                pout1 = np.append(pout1,work[i])
    xlab = 'Orbital Phase ($\phi$)'

# clean up y-axis units

    if status == 0:

        nrm = len(str(int(pout1[np.isfinite(pout1)].max())))-1


        pout1 = pout1 / 10**nrm
        pout2 = pout2 / 10**nrm
        if nrm == 0:
            ylab = plotlab
        else:
            ylab = '10$^%d$ %s' % (nrm, plotlab)

# data limits

        xmin = ptime1.min()
        xmax = ptime1.max()
        ymin = pout1[np.isfinite(pout1)].min()
        ymax = pout1[np.isfinite(pout1)].max()
        xr = xmax - xmin
        yr = ymax - ymin
        ptime1 = np.insert(ptime1,[0],[ptime1[0]])
        ptime1 = np.append(ptime1,[ptime1[-1]])
        pout1 = np.insert(pout1,[0],[0.0])
        pout1 = np.append(pout1,0.0)
        if bindata:
            ptime2 = np.insert(ptime2,[0],ptime2[0] - 1.0 / nbins)
            ptime2 = np.insert(ptime2,[0],ptime2[0])
            ptime2 = np.append(ptime2,[ptime2[-1] + 1.0 / nbins, ptime2[-1] + 1.0 / nbins])
            pout2 = np.insert(pout2,[0],[pout2[-1]])
            pout2 = np.insert(pout2,[0],[0.0])
            pout2 = np.append(pout2,[pout2[2],0.0])

# plot new light curve

    if status == 0 and plottype != 'none':
        plt.figure(figsize=[17,7])
        plt.clf()
        ax = plt.axes([0.06,0.11,0.93,0.86])
        plt.gca().xaxis.set_major_formatter(plt.ScalarFormatter(useOffset=False))
        plt.gca().yaxis.set_major_formatter(plt.ScalarFormatter(useOffset=False))
        labels = ax.get_yticklabels()
        plt.setp(labels, 'rotation', 90)
        if bindata:
            plt.fill(ptime2,pout2,color=fcolor,linewidth=0.0,alpha=falpha)
        else:
            if 'det' in plottype:
                plt.fill(ptime1,pout1,color=fcolor,linewidth=0.0,alpha=falpha)
        plt.plot(ptime1,pout1,color=lcolor,linestyle='',linewidth=lwidth,marker='.')
        if bindata:
            plt.plot(ptime2[1:-1],pout2[1:-1],color='r',linestyle='-',linewidth=lwidth,marker='')
        plt.xlabel(xlab, {'color' : 'k'})
        plt.ylabel(ylab, {'color' : 'k'})
        plt.xlim(-0.49999,1.49999)
        if ymin >= 0.0:
            plt.ylim(ymin-yr*0.01,ymax+yr*0.01)
#            ylim(0.96001,1.03999)
        else:
            plt.ylim(1.0e-10,ymax+yr*0.01)
        plt.grid()
        plt.ion()
        plt.show()

# close input file

    if status == 0:
        status = kepio.closefits(instr,logfile,verbose)

# stop time

    kepmsg.clock('KEPFOLD ended at: ',logfile,verbose)

# main
if '--shell' in sys.argv:
    import argparse

    parser = argparse.ArgumentParser(description='Low bandpass or high bandpass signal filtering')

    parser.add_argument('--shell', action='store_true', help='Are we running from the shell?')

    parser.add_argument('infile', help='Name of input file', type=str)
    parser.add_argument('outfile', help='Name of FITS file to output', type=str)
    parser.add_argument('--period', help='Period to fold data upon [days]', type=float)
    parser.add_argument('--bjd0', help='time of zero phase for the folded period [BJD]', type=float)
    parser.add_argument('--bindata', action='store_true', help='Bin output data?')
    parser.add_argument('--binmethod', default='mean', help='Binning method',
                        type=str, choices=['mean','median','sigclip'])
    parser.add_argument('--threshold', default=1.0,
                        help='Sigma clipping threshold [sigma]', type=float)
    parser.add_argument('--niter', default=5,
                        help='Number of sigma clipping iterations before giving up', type=int)
    parser.add_argument('--nbins', default=1000, help='Number of period bins', type=int)
    parser.add_argument('--quality', action='store_true', help='Reject bad quality timestamps?')
    parser.add_argument('--plottype', default='sap', help='plot type',
                        type=str, choices=['sap','pdc','cbv','det','none'])
    parser.add_argument('--plotlab', default='e$^-$ s$^{-1}$', help='Plot axis label', type=str)
    parser.add_argument('--clobber', action='store_true', help='Overwrite output file?')
    parser.add_argument('--verbose', action='store_true', help='Write to a log file?')
    parser.add_argument('--logfile', '-l', help='Name of ascii log file',
                        default='kepfold.log', dest='logfile', type=str)
    parser.add_argument('--status', '-e', help='Exit status (0=good)',
                        default=0, dest='status', type=int)

    args = parser.parse_args()

    cmdLine=True

    kepfold(args.infile,args.outfile,args.period,args.bjd0,args.bindata,args.binmethod,args.threshold,
            args.niter,args.nbins,args.quality,args.plottype,args.plotlab,args.clobber,args.verbose,
            args.logfile,args.status,cmdLine)

else:
    from pyraf import iraf
    parfile = iraf.osfn("kepler$kepfold.par")
    t = iraf.IrafTaskFactory(taskname="kepfold", value=parfile, function=kepfold)
