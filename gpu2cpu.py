from keras import layers as kl 
from keras.models import Model
encoder_input = kl.Input(shape=(None,))
decoder_input = kl.Input(shape=(None,))
is_mask=False
n_chars=100
n_chars_p=n_chars+2+is_mask
lstm_f=kl.LSTM# if is_mask else kl.CuDNNLSTM
encoder = kl.Embedding(n_chars_p, 16, mask_zero=is_mask)(encoder_input)
encoder = lstm_f(128, return_sequences=True)(encoder)
encoder_outputs, state_h, state_c = lstm_f(128, return_sequences=True,return_state=True)(encoder)
#encoder = lstm_f(64, return_sequences=False,return_state=False)(encoder)

decoder = kl.Embedding(n_chars_p, 16, mask_zero=is_mask)(decoder_input)
decoder = lstm_f(128, return_sequences=True)(decoder, initial_state=[state_h, state_c])
decoder = lstm_f(128, return_sequences=True)(decoder)

#output = kl.TimeDistributed(kl.Dense(n_chars_p, activation="softmax"))(decoder)


attention = kl.dot([decoder, encoder_outputs], axes=[2, 2])
attention = kl.Activation('softmax')(attention)

context = kl.dot([attention, encoder_outputs], axes=[2,1])
decoder_combined_context = kl.concatenate([context, decoder])

# Has another weight + tanh layer as described in equation (5) of the paper
output = kl.TimeDistributed(kl.Dense(n_chars_p, activation="tanh"))(decoder_combined_context) # equation (5) of the paper
output = kl.TimeDistributed(kl.Dense(n_chars_p, activation="softmax"))(output) # equation (6) of the paper

model = Model(inputs=[encoder_input, decoder_input], outputs=output)
model.compile(optimizer='adamax', loss='categorical_crossentropy')

model.load_weights('model.h5')
model.save("model_cpu.h5")