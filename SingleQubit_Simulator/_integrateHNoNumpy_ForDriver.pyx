#cython: boundscheck=False
#cython: wraparound=False
import numpy as np
cimport numpy as np 

def integrateH(np.ndarray[double, ndim=1] vStart, np.ndarray[double, ndim=1] vTime, \
  np.ndarray[double, ndim=1] vDelta, np.ndarray[double, ndim=1] vDetuning, int nReshape):
    # simulate the time evolution for the start state vStart
    # a state is defined as [Psi0 Psi1]'
    # a vector of states is a matrix, defined as [state1 state2 ... stateN]
    #
    # pre-allocate space for the output variable
    cdef unsigned int n1
    cdef complex U11, U12, U21, U22
    cdef np.ndarray[complex, ndim=2] mState = np.zeros((2,len(vTime)), dtype='complex')
    # use start vector for the first entry
    mState[:,0] = vStart
    # get time steps
    cdef np.ndarray[double, ndim=1] vDTime = np.diff(vTime)
    # precalc vectors
    n = len(vDelta)
    cdef np.ndarray[double, ndim=1] vEnergy = 0.5*np.sqrt(vDelta[0:n-1]**2 + vDetuning[0:n-1]**2)
    cdef np.ndarray[double, ndim=1] vAngle = 2*np.pi*vEnergy*vDTime
    cdef np.ndarray[double, ndim=1] vCos = np.cos(vAngle)
    cdef np.ndarray[double, ndim=1] vSinEn = np.sin(vAngle)/vEnergy

    # apply hamiltonian N times
    for n1 in range(len(vDTime)):
        U11 = vCos[n1] + 1j*0.5*vDetuning[n1]*vSinEn[n1]
        U12 = 1j*0.5*vDelta[n1]*vSinEn[n1]
        U21 = 1j*0.5*vDelta[n1]*vSinEn[n1]
        U22 = vCos[n1] - 1j*0.5*vDetuning[n1]*vSinEn[n1]
        mState[0,n1+1] = U11 * mState[0,n1] + U12 * mState[1,n1]
        mState[1,n1+1] = U21 * mState[0,n1] + U22 * mState[1,n1]
    # reshape data to reduce vector size
    if nReshape>1:
       mState = mState[:,0::nReshape]
    return mState


def integrateHy(np.ndarray[double, ndim=1] vStart, np.ndarray[double, ndim=1] vTime, \
  np.ndarray[double, ndim=1] vDelta, np.ndarray[double, ndim=1] vDetuning, \
  np.ndarray[double, ndim=1] vY, int nReshape):
    # simulate the time evolution for the start state vStart
    # a state is defined as [Psi0 Psi1]'
    # a vector of states is a matrix, defined as [state1 state2 ... stateN]
    #
    # pre-allocate space for the output variable
    cdef unsigned int n1
    cdef complex U11, U12, U21, U22
    cdef np.ndarray[complex, ndim=2] mState = np.zeros((2,len(vTime)), dtype='complex')
    # use start vector for the first entry
    mState[:,0] = vStart
    # get time steps
    cdef np.ndarray[double, ndim=1] vDTime = np.diff(vTime)
    # precalc vectors
    n = len(vDelta)
    cdef np.ndarray[double, ndim=1] vEnergy = \
        0.5*np.sqrt(vDelta[0:n-1]**2 + vDetuning[0:n-1]**2 + vY[0:n-1]**2)
    cdef np.ndarray[double, ndim=1] vAngle = 2*np.pi*vEnergy*vDTime
    cdef np.ndarray[double, ndim=1] vCos = np.cos(vAngle)
    cdef np.ndarray[double, ndim=1] vSinEn = np.sin(vAngle)/vEnergy
    # take care of sin(x)/x division by zero
    nan_indx = np.isnan(vSinEn)
    vSinEn[nan_indx] = 2 * np.pi * vDTime[nan_indx]

    # apply hamiltonian N times
    for n1 in range(len(vDTime)):
        U11 = vCos[n1] + 1j*0.5*vDetuning[n1]*vSinEn[n1]
        U12 = (vY[n1] + 1j * vDelta[n1]) * 0.5 * vSinEn[n1]
        U21 = (-vY[n1] + 1j * vDelta[n1]) * 0.5 * vSinEn[n1]
        U22 = vCos[n1] - 1j*0.5*vDetuning[n1]*vSinEn[n1]
        mState[0,n1+1] = U11 * mState[0,n1] + U12 * mState[1,n1]
        mState[1,n1+1] = U21 * mState[0,n1] + U22 * mState[1,n1]
    # reshape data to reduce vector size
    if nReshape>1:
       mState = mState[:,0::nReshape]
    return mState


def integrateH_RWA(np.ndarray[double, ndim=1] vStart, np.ndarray[double, ndim=1] vTime, \
  np.ndarray[double, ndim=1] vDelta, np.ndarray[double, ndim=1] vDetX,
  np.ndarray[double, ndim=1] vDetY, int nReshape):
    # simulate the time evolution for the start state vStart
    # a state is defined as [Psi0 Psi1]'
    # a vector of states is a matrix, defined as [state1 state2 ... stateN]
    #
    # pre-allocate space for the output variable
    cdef unsigned int n1
    cdef complex U11, U12, U21, U22
    cdef np.ndarray[complex, ndim=2] mState = np.zeros((2,len(vTime)), dtype='complex')
    # use start vector for the first entry
    mState[:,0] = vStart
    # get time steps
    cdef np.ndarray[double, ndim=1] vDTime = np.diff(vTime)
    # precalc vectors
    n = len(vDelta)
    cdef np.ndarray[double, ndim=1] vEnergy = 1E-200 + 0.5*np.sqrt(vDelta[0:n-1]**2 + vDetX[0:n-1]**2 + vDetY[0:n-1]**2)
    cdef np.ndarray[double, ndim=1] vAngle = 2*np.pi*vEnergy*vDTime
    cdef np.ndarray[double, ndim=1] vCos = np.cos(vAngle)
    cdef np.ndarray[double, ndim=1] vSinEn = np.sin(vAngle)/vEnergy

    # apply hamiltonian N times
    for n1 in range(len(vDTime)):
        U11 = vCos[n1] + 1j*0.5*vDetX[n1]*vSinEn[n1]
        U12 = 0.5*(1j*vDelta[n1] - vDetY[n1]) * vSinEn[n1]
        U21 = 0.5*(1j*vDelta[n1] + vDetY[n1]) * vSinEn[n1]
        U22 = vCos[n1] - 1j*0.5*vDetX[n1]*vSinEn[n1]
        mState[0,n1+1] = U11 * mState[0,n1] + U12 * mState[1,n1]
        mState[1,n1+1] = U21 * mState[0,n1] + U22 * mState[1,n1]
    # reshape data to reduce vector size
    if nReshape>1:
       mState = mState[:,0::nReshape]
    return mState

#    mSx = np.array([[0.,1.],[1.,0.]])
#    mSy = np.array([[0.,-1j],[1j,0.]])
#    mSz = np.array([[1.,0.],[0.,-1.]])
#    # apply hamiltonian N times
#    for n1, dTime in enumerate(vDTime):
#       # define hamiltonian
#       H = -0.5 * (mSx*vDelta[n1] + mSz*vDetuning[n1])
#       # define time-evolution operator
#       U = mIdentity * vCos[n1] - 1j*H*vSin[n1]/vEnergy[n1]
#       # calculate next state
#       mState[:,n1+1] = np.dot(U,mState[:,n1])

def goToRotatingFrame(np.ndarray[complex, ndim=2] mState, \
    np.ndarray[double, ndim=1] vTime, double dDriveFreq, double dTimeZero):
        # init variables
        cdef unsigned int n2
        cdef complex A11
        cdef complex A22
        # perform rotations around Z
        for n2 in range(len(vTime)):
            A11 = np.exp(-1j*np.pi*dDriveFreq*(vTime[n2]-dTimeZero))
            A22 = 1/A11
            mState[0,n2] = A11*mState[0,n2] 
            mState[1,n2] = A22*mState[1,n2]
        return mState
