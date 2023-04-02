from keras.models import load_model
import pickle
import numpy as np
import os
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID" 
os.environ["CUDA_VISIBLE_DEVICES"] = ""
with open("all_chars_map.pkl",'rb') as fp:
	all_chars_map=pickle.load(fp)

model=load_model("model.h5")


def chat(inputs,temp=1):
	inputs=np.array([[0]+list(map(all_chars_map.get,inputs))+[1]])
	res=''
	a_i=[0]
	for i in range(50):
		output=model.predict([inputs,np.array([a_i])])[0][-1]
		output=np.log(output + 1e-8) / temp
		output = np.exp(output)
		output = output / np.sum(output)
		output=np.random.choice(np.arange(len(output)),p=output)
		if output==1:
			break
		else:
			res+=all_chars_map[output]
			a_i+=[output]
	return res

while True:
	print()
	print("write down the temp")
	print("--> ",end='')
	temp=float(input())
	print("write down the question")
	print("--> ",end='')
	print(chat(input(),temp=temp))