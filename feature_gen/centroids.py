import pickle
import numpy as np

def compute_centroids( data ):

    label_colMapD = data['label_colMapD']
    featM         = data['featM']
    labelL        = data['labelL']

    presetTypeN = len(label_colMapD)
    featDimN    = featM.shape[1]
    
    centroidM = np.zeros((featDimN,presetTypeN))
    cntV = [0] * presetTypeN
    for row_idx,labelV in enumerate(labelL):

        for i, order in enumerate(labelV):
            if order != 0:
                centroidM[:,i] += featM[row_idx,:]
                cntV[i] += 1

    for i in range(presetTypeN):
        centroidM[:,i] /= cntV[i]

    return centroidM

def distance( centroidM, featV ):
    xV = np.linalg.norm(centroidM - featV[:, np.newaxis], axis=0)
    return xV / sum(xV)

def cosine_distance( matrix, vector ):
    # 2. Compute the dot product between each row and the vector
    dot_products = np.dot(matrix, vector)

    # 3. Compute the L2 norm (magnitude) for each row and the vector
    row_norms = np.linalg.norm(matrix, axis=1)
    vector_norm = np.linalg.norm(vector)

    # 4. Calculate Cosine Similarity 
    cosine_similarity = dot_products / (row_norms * vector_norm)

    # 5. Calculate Cosine Distance
    cosine_dist = 1 - cosine_similarity

    return cosine_dist

def print_distance_stats(data,centroidM):

    label_colMapD = data['label_colMapD']
    featM         = data['featM']
    labelL        = data['labelL']

    presetTypeN = len(label_colMapD)
    featDimN    = featM.shape[1]
    exampleN    = featM.shape[0]
    accV        = np.zeros((presetTypeN,))

    assert featDimN == centroidM.shape[0]
    assert exampleN == len(labelL)

    print(centroidM.shape,featM[0,:].shape )

    for row_idx,labelV in enumerate(labelL):

        
        # accV += distance(centroidM,featM[row_idx,:])
        accV += cosine_distance(np.transpose(centroidM),featM[row_idx,:])
        
        
    accV /= exampleN
    print(accV)
    print(np.mean(accV))
    print(np.std(accV))

if __name__ == "__main__":

    train_data_fname      = "output/training_0.pkl"

    
    with open(train_data_fname,'rb') as f:
        data = pickle.load(f)
    
    centroidM = compute_centroids( data )
    print_distance_stats(data,centroidM)
