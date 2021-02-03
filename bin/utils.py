import copy
import dill as pickle
import h5py
import io
import numpy as np
import sklearn.preprocessing
import tensorflow as tf



transforms = {
    'log2': sklearn.preprocessing.FunctionTransformer(func=np.log2, inverse_func=lambda x: 2 ** x)
}



class KerasRegressor(tf.keras.wrappers.scikit_learn.KerasRegressor):
    '''
    TensorFlow Keras API neural network regressor.

    Workaround the tf.keras.wrappers.scikit_learn.KerasRegressor serialization
    issue using BytesIO and HDF5 in order to enable pickle dumps.

    Adapted from: https://github.com/keras-team/keras/issues/4274#issuecomment-519226139
    '''

    def __getstate__(self):
        state = self.__dict__
        if 'model' in state:
            model = state['model']
            model_hdf5_bio = io.BytesIO()
            with h5py.File(model_hdf5_bio, mode='w') as file:
                model.save(file)
            state['model'] = model_hdf5_bio
            state_copy = copy.deepcopy(state)
            state['model'] = model
            return state_copy
        else:
            return state

    def __setstate__(self, state):
        if 'model' in state:
            model_hdf5_bio = state['model']
            with h5py.File(model_hdf5_bio, mode='r') as file:
                state['model'] = tf.keras.models.load_model(file)
        self.__dict__ = state