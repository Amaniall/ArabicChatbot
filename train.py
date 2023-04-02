import pickle
from os import listdir
from tqdm import tqdm
import numpy as np 
np.random.seed(0)
users_files=listdir("users")

chars_c=set('abcdefghijklmnopqrstuvwxyzابتثجحخدذرزسشصضطظعغفقكلمنهوىي')
data=[]
for file in users_files:
	try:
		with open('users/'+file,'rb') as fp:
			data.extend(pickle.load(fp))
	except EOFError:
		pass

print(len(data))
qq=dict()
questions=[]
answers=[]
from collections import Counter
import re
chars=Counter()
for (q,a) in tqdm(data):
	if len(chars_c-set(q))!=len(chars_c) and 1<len(a)<280 and 4<len(q)<280 and len(re.findall('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', q+' '+a))==0:
		if q not in qq:
			qq[q]=None
			q=q.lower().replace("<br>",'\n').replace("<br/>","\n").replace("</br>",'\n')
			a=a.lower().replace("<br>",'\n').replace("<br/>","\n").replace("</br>",'\n')
			questions.append(q)
			chars.update(q)
			answers.append(a)
			chars.update(a)

print(len(questions))
del(qq)
del(chars['�'])
is_mask=False
n_chars=100
n_chars=min(n_chars,len(chars))
all_chars=[i[0] for i in chars.most_common(n_chars)]
indexes=np.arange(n_chars)+2+is_mask
indexes=indexes.tolist()
n_chars_p=n_chars+2+is_mask
all_chars_map=dict(list(zip(all_chars,indexes)) + list(zip(indexes,all_chars)))
with open("all_chars_map.pkl",'wb') as fp:
	pickle.dump(all_chars_map,fp)

questions=[[all_chars_map[char] for char in s if char in all_chars_map] for s in questions]
answers=[[all_chars_map[char] for char in s if char in all_chars_map] for s in answers]

indexss=[i for i,(q,a) in enumerate(zip(questions,answers)) if (1<len(q)) and (1<len(a))]
questions=[questions[i] for i in indexss]
answers=[answers[i] for i in indexss]

from keras import layers as kl 
from keras.models import Model

import tensorflow as tf 
import keras.backend as K
with K.tf.device('/gpu:0'):
	gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.7)
	sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options))
	K.set_session(sess)
	
encoder_input = kl.Input(shape=(None,))
decoder_input = kl.Input(shape=(None,))
lstm_f=kl.LSTM if is_mask else kl.CuDNNLSTM
encoder = kl.Embedding(n_chars_p, 16, mask_zero=is_mask)(encoder_input)
encoder = lstm_f(128, return_sequences=True)(encoder)
encoder_outputs, state_h, state_c = lstm_f(128, return_sequences=True,return_state=True)(encoder)

decoder = kl.Embedding(n_chars_p, 16, mask_zero=is_mask)(decoder_input)
decoder = lstm_f(128, return_sequences=True)(decoder, initial_state=[state_h, state_c])
decoder = lstm_f(128, return_sequences=True)(decoder)

attention = kl.dot([decoder, encoder_outputs], axes=[2, 2])
attention = kl.Activation('softmax')(attention)

context = kl.dot([attention, encoder_outputs], axes=[2,1])
decoder_combined_context = kl.concatenate([context, decoder])

output = kl.TimeDistributed(kl.Dense(n_chars_p, activation="tanh"))(decoder_combined_context) 
output = kl.TimeDistributed(kl.Dense(n_chars_p, activation="softmax"))(output)

model = Model(inputs=[encoder_input, decoder_input], outputs=output)
model.compile(optimizer='adamax', loss='categorical_crossentropy')
print(model.summary())

def padder(*xs):
	res=tuple()
	for x in xs:
		maxa=max([len(i) for i in x])
		res+=([([0]*(maxa-len(i)))+i for i in x],)
	return res

eye=np.eye(n_chars_p)
def generator(questions,answers,batch_size=1):
	batch_size=batch_size if is_mask else 1
	q_is,a_is,a_os=[],[],[]
	for q,a in tqdm(zip(questions,answers),total=len(questions)):
		q_is.append([0+is_mask]+q+[1+is_mask])
		a_is.append([0+is_mask]+a)
		a_os.append(a+[1+is_mask])
		if len(q_is)==batch_size:
			q_is,a_is,a_os=padder(q_is,a_is,a_os)
			yield [np.array(q_is),np.array(a_is)],eye[np.array(a_os,dtype=int)]
			q_is,a_is,a_os=[],[],[]
	if len(q_is)>0:
		q_is,a_is,a_os=padder(q_is,a_is,a_os)
		yield [np.array(q_is),np.array(a_is)],eye[np.array(a_os,dtype=int)]
		q_is,a_is,a_os=[],[],[]

def chat(inputs):
	inputs=np.array([[0]+list(map(all_chars_map.get,inputs))+[1]])
	res=''
	a_i=[0]
	for i in range(50):
		output=model.predict([inputs,np.array([a_i])])
		output=np.random.choice(np.arange(len(output[0][-1])),p=output[0][-1])
		if output==1:
			break
		else:
			res+=all_chars_map[output]
			a_i+=[output]
	return 'None' if len(res)==0 else res

from time import time
class timer:
	def __init__(self,wait):
		self.wait=wait
		self.t=time()
	def check(self):
		t=time()
		if (self.wait+self.t)<=t:
			self.t=t
			return True
		else:
			return False

timer_l=timer(0.5)
timer_c=timer(5)
test_ce='how are you'
test_ca='كيف حالك'
n_epochs=9999999999
from tqdm import trange
for epoch in range(n_epochs):
	res=[]
	i_s=0
	for i,(x,y) in enumerate(generator(questions,answers,batch_size=1)):
		res.append(model.train_on_batch(x,y))
		if timer_l.check():
			trange(1,desc='loss={}'.format(np.mean(res[i_s:i],axis=0)),position=1,bar_format='{desc}')
			i_s=i
		if timer_c.check():
			trange(1,desc=' '*100,position=2,bar_format='{desc}')
			trange(1,desc=' '*100,position=3,bar_format='{desc}')
			trange(1,desc='[{}={}]'.format(test_ce,chat(test_ce).replace("\n",' ')),position=2,bar_format='{desc}')
			trange(1,desc='[{}={}]'.format(test_ca,chat(test_ca).replace("\n",' ')),position=3,bar_format='{desc}')

	print("loss={}".format(np.mean(res,axis=0)))
	print('='*20 + 'epoch:{}'.format(epoch) + '='*20)
	model.save("model.h5")



