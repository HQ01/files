import minpy.numpy as np
from minpy.nn.model_builder import *
from minpy.nn.modules import *
#from examples.utils.data_utils import get_CIFAR10_data
'''
this script requires you to download cifar_10_train/val.rec first
should be placed under minpy/examples/nn/
'''

class VGG(Model):
	def __init__(self,block_number,block_configs,filter_numbers):
		super(VGG,self).__init__(loss = 'softmax_loss')
		assert block_number == len(block_configs) == len(filter_numbers)
		block_param_name = []
		for i in xrange(block_number):
			block_param_name.append("block%d"%i)
		params = dict(zip(block_param_name,zip(block_configs,filter_numbers)))
		#print params['block0']
		self._blocks = tuple(
			VGG._block(params["block%d"%i])
			for i in xrange(block_number)
			)

		self._to_scores = Sequential(
			BatchNorm(fix_gamma = False),
			FullyConnected(num_hidden = 4096),
			FullyConnected(num_hidden = 4096),
			FullyConnected(num_hidden = 10)
			)
		
	def forward(self,data,mode = 'training'):
		if mode == 'training': self.training()
		elif mode == 'inference': self.inference()

		data = data

		for block in self._blocks:
			data = block(data)

		return self._to_scores(data)


	@staticmethod
	def _convolution(**kwargs):
		defaults = {'kernel':(3,3),'stride':(1,1),'pad':(1,1),'no_bias':True}
		defaults.update(kwargs)
		return Sequential(
			BatchNorm(fix_gamma = False),
			ReLU(),
			Convolution(**defaults)
			)
	@staticmethod
	def _pooling(**kwargs):
		defaults = {'pool_type' : 'max','kernel' : (2,2),'stride' : (2,2), 'pad' : (0,0)}
		defaults.update(kwargs)
		return Sequential(
			Pooling(**defaults)
			)
	@staticmethod
	def _block(args):
		#print 'attention!!!!',args
		layer_number, filter_number = args
		block = Sequential ()
		for i in xrange(layer_number):
			block.append(
				VGG._convolution(num_filter = filter_number)
				)
		block.append(
			VGG._pooling()
			)

		return block

unpack_batch = lambda batch : (batch.data[0].asnumpy(),batch.label[0].asnumpy())


if __name__ == '__main__':
	from argparse import ArgumentParser
	parser = ArgumentParser()
	parser.add_argument('--data_dir',type = str,required = True, help = 'Directory that contains cifar10 data')
	parser.add_argument('--gpu_index', type = int, default = 0)
	args = parser.parse_args()
	#image_data = get_CIFAR10_data(args.data_dir)
	#train_data_iter = NDArrayIter(data = image_data['X_train'],
								  #label = data['y_train'],
								  #batch_size = batch_size,
								  #shuffle = True)
	#test_dataiter = NDArrayIter(data = data['X_test'],
								#label = data['y_test'] 
								#batch_size = batch_size
								#shuffle = False)
	from load_cifar10_data_iter import *
	train_data_iter, val_data_iter = load_cifar10_data_iter(batch_size = 32,path = args.data_dir)

	from minpy.context import set_context, cpu,gpu

	set_context(gpu(args.gpu_index))

	model = VGG(5,(2,2,3,3,3),(64,128,256,512,512))
	updater = Updater(model,update_rule = 'sgd',learning_rate = 0.1,momentem = 0.9)

	epoch_number = 0
	iteration_number = 0

	terminated = False

	while not terminated:
		#training 
		epoch_number +=1

		train_data_iter.reset()

		for iteration,batch in enumerate(train_data_iter):
			iteration_number +=1
			if iteration_number > 64000:
				terminated = True
				break
			if iteration_number in (32000,48000):
				updater.learning_rate *= 0.1
			
			data,labels = unpack_batch(batch)
			loss = model(data,labels = labels)
			grad_dict = model.backward()
			updater(grad_dict)

			if iteration_number  % 100 == 0:
				print 'iteration %d loss %f' %(iteration_number,loss)

		print 'now is validation\n'

		val_data_iter.reset()
		errors,samples = 0,0
		for batch in validation_iter:
			data,labels = unpack_batch(batch)
			scores = model.forward(data,'inference')
			predictions = np.argmax (scores, axis = 1)
			errors += np.count_nonzero(predictions - labels)
			samples += len(data)


		print 'epoch %d validation error %f' % (epoch_number, errors/float(samples))

