import numpy as np
from scipy.interpolate import InterpolatedUnivariateSpline


###########################################################


def fluxFromFrequency(f, f_max, asymmetry, f_offset=0):
	F = (f - f_offset)/f_max
	d = (asymmetry-1)/(asymmetry+1)
	flux = 1/np.pi * np.arccos(np.sqrt((F**4 - d**2)/(1 - d**2)))
	return flux

def frequencyFromFlux(flux, f_max, asymmetry, f_offset=0):
	d = (asymmetry-1)/(asymmetry+1)
	return f_max * np.sqrt(np.sqrt(d**2 + (1 - d**2)*np.cos(np.pi*(flux))**2))


###########################################################

class FrequencyControl():

	def __init__(self):
		self.qubits = []
		self.numQubits = 0
		self.target_frequencies = []

	def add_qubit(self, filename):
		try:
			qb = Transmon(self.numQubits, filename)
			self.qubits.append(qb)
			print('*** added qubit {} from trace {}'.format(self.numQubits, filename))
			self.numQubits += 1
			self.target_frequencies.append(qb.f_max)
		except(IOError):
			raise ValueError('please specify filename of qubit trace!')

	def add_qubit_fit(self, params):
		qb = Transmon(self.numQubits, params=params)
		self.qubits.append(qb)
		print('*** added qubit {} from params {}'.format(self.numQubits, params))
		self.numQubits += 1
		self.target_frequencies.append(qb.f_max)


	def remove_qubit(self, i):
		del self.qubits[i]
		del self.target_frequencies[i]
		self.numQubits -= 1

	def get_fluxes(self):
		fluxes = []
		for qb in self.qubits:
			fluxes.append(qb.get_flux())
		return np.array(fluxes)

	def set_target_frequencies(self, frequencies, qubits=[]):
		if len(frequencies) > self.numQubits:
			raise ValueError('too many frequencies given for {} qubits'.format(self.numQubits))
		if qubits == []:
			qubits = range(len(frequencies))
		for i, qb in enumerate(qubits):
			self.target_frequencies[qb] = frequencies[i]
			self.qubits[qb].set_target_frequency(frequencies[i])

	def get_frequencies(self, fluxes):
		frequencies = []
		for qb, flux in zip(self.qubits, fluxes):
			frequencies.append(qb.get_frequency(flux))
		return np.array(frequencies)



class Transmon():

	def __init__(self, index, filename=None, params=None):
		self.index = index
		self.target_frequency = None
		self.trace = None
		self.f_offset = 0
		self.positive_flux = True
		if filename is not None:
			self.get_trace(filename)
		if params is not None and len(params)==2:
			self.get_trace_fit(params[0], params[1])


	def set_target_frequency(self, f):
		if f > self.f_max: 
			raise ValueError('frequency too high for transmon {}!'.format(self.index+1))
		elif f < self.f_min:
			raise ValueError('frequency too low for transmon {}!'.format(self.index+1))  
		else:
			self.target_frequency = f

	def set_offset(self, offset):
		self.f_offset = offset

	def get_trace(self, filename):
		trace = np.load(filename)
		flux = np.linspace(-0.5 , 0.5, trace.size)
		self.trace = trace[~np.isnan(trace)]
		self.flux = flux[~np.isnan(trace)]
		self.f_max = np.max(self.trace)
		self.f_min = np.min(self.trace)
		self.target_frequency = self.f_max

	def get_trace_fit(self, f_max, asymmetry):
		flux = np.linspace(-0.5 , 0.5, 1000)
		trace = frequencyFromFlux(flux, f_max, asymmetry)
		self.trace = trace
		self.flux = flux
		self.f_max = np.max(self.trace)
		self.f_min = np.min(self.trace)
		self.target_frequency = self.f_max



	def get_flux(self):
		f = self.target_frequency + self.f_offset
		# if (f > self.f_max).any() or (f < self.f_min).any():
		# 	raise ValueError('*** ERROR: frequency outside tunable range for transmon {}'.format(self.index+1))
		# 	return
		
		if f >= self.f_max:
			flux = 0
		elif f == self.f_min:
			flux = 0.5
			if not self.positive_flux:
				flux = -flux 
		elif f < self.f_min:
			spline = InterpolatedUnivariateSpline(self.flux, self.trace - (self.target_frequency - self.f_offset))
			fluxes = spline.roots()
			flux = 0.5 + (0.5 - max(fluxes))
			if not self.positive_flux:
				flux = -0.5 - np.abs(min(fluxes) + 0.5)
		else:
			spline = InterpolatedUnivariateSpline(self.flux, self.trace - f)
			fluxes = spline.roots()
			if self.positive_flux:
				try: flux = max(fluxes)
				except: flux = 0
			else:
				try: flux = min(fluxes)
				except: flux = 0

		return flux


	def get_frequency(self, flux):
		if (flux < -0.5).any() or (flux > 0.5).any():
			raise ValueError('*** ERROR: flux outside +- 0.5 for transmon {}'.format(self.index+1))
			return
		spline = InterpolatedUnivariateSpline(self.flux, self.trace)
		return spline(flux) - self.f_offset



	# def get_flux(self, positive_flux=True):
	# 	f = self.target_frequency
	# 	if (f > self.f_max).any() or (f < self.f_min).any():
	# 		raise ValueError('frequency outside tunable range for transmon {}'.format(self.index))
	# 		pass
	# 	if positive_flux:
	# 		trace = self.trace[self.flux > 0]
	# 		trace = trace[::-1]	
	# 		#data for np.interp needs to be increasing!!
	# 		flux = self.flux[self.flux > 0]
	# 		flux = flux[::-1]
	# 	else:
	# 		trace = self.trace[self.flux < 0]
	# 		flux = self.flux[self.flux < 0]
	# 	return np.interp(f, trace, flux)

	# def get_frequency(self, flux):
	# 	if flux < -0.5 or flux > 0.5:
	# 		raise ValueError('flux outside +- 0.5 for transmon {}'.format(self.index))
	# 		pass
	# 	return np.interp(flux, self.flux, self.trace)


if __name__ == '__main__':
	pass
