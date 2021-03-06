import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
from torchvision import datasets
import torchvision
import os
import matplotlib
matplotlib.use('agg')
import pickle
import copy
import h5py
import pandas as pd
import random
import os
import sys
sys.path.insert(0, './core')
# Custom import
import dataLoading
import utils
from lossfunctions import *
from shading import *
import models
from utils import PRINT
from train import *

SHOW_IMAGES = False
load_syn = True
load_GAN = False #True
train_syn = False
train_GAN = True
FirstRun = False
gan_epochs = 50
syn_epochs = 200
exp_name = 'resnet_SfSNet_SIRFS_SH_GAN'
LOCAL_MACHINE = False
output_path = './resnet_SfSNet_SIRFS_SH_GAN/'
synthetic_image_dataset_path = './data/synHao/'
sfs_net_path = '/home/bsonawane/Thesis/LightEstimation/SIRFS/synImages/'   #scripts/SfsNet_SynImage_back/'
sfs_net_val_path = '/home/bsonawane/Thesis/LightEstimation/SIRFS/synImagesAlbedo/'

if LOCAL_MACHINE:
    real_image_dataset_path = '../../Light-Estimation/datasets/realImagesSH/'
else:
    real_image_dataset_path = '/home/bsonawane/Thesis/LightEstimation/SIRFS/realData/data/'


if FirstRun == True:
    os.mkdir(output_path)
    os.mkdir(output_path+'images/')
    os.mkdir(output_path+'val/')
    os.mkdir(output_path+'models/')
    os.mkdir(output_path+'savedModels/')


real_image_mask = '/home/bsonawane/Thesis/LightEstimation/SIRFS/realData/mask/'
global_batch_size = 64

#if not os.path.exists(output_image_path):
#    os.makedirs(output_image_path)

# Helper routines
IS_CUDA = False
if torch.cuda.is_available():
    IS_CUDA = True

def save_shading(normal, sh, real_image_mask, path, name, shadingFromNet = False, Predicted = False):
    if Predicted == False:
        normal = denorm(normal)
    outShadingB = ShadingFromDataLoading(normal, sh, shadingFromNet = True)
    if Predicted == True:
        outShadingB = denorm(outShadingB)
    outShadingB = applyMask(outShadingB, real_image_mask)
    outShadingB = outShadingB.data
    #pic = torchvision.utils.make_grid(outShadingB, padding=1)
    save_image(outShadingB, path + name+'.png')
    save_image(outShadingB[0], path + name+'_0.png')
    return outShadingB

def to_numpy(v):
    return v.cpu().data.numpy()

def save_results_h5(true_fixed_normal, sirfs_fixed_normal, tfSH, fSH, mask, output_path):
    hf = h5py.File(output_path+'results.h5', 'w')
    t_f_normal = true_fixed_normal #denorm(true_fixed_normal)
    s_f_normal = sirfs_fixed_normal #denorm(sirfs_fixed_normal)
    t_f_normal = applyMask(t_f_normal, mask)
    #s_f_normal = applyMask(s_f_normal, mask)

    hf.create_dataset('true_normal', data = to_numpy(t_f_normal))
    hf.create_dataset('sirfs_normal', data = to_numpy(s_f_normal))
    hf.create_dataset('expected_sh', data = tfSH)
    hf.create_dataset('predicted_sh', data = fSH)
    hf.create_dataset('mask', data = to_numpy(var(mask)))
    hf.close()

def var(x):
    if IS_CUDA:
        x = x.cuda()
    return Variable(x)
# End of Helper routines

# Load synthetic dataset
syn_image1, syn_image2, syn_label = dataLoading.load_synthetic_ldan_data(synthetic_image_dataset_path, batch_size = global_batch_size)
#real_image, sirfs_normal, sirfs_SH, sirfs_shading, real_image_val, sirfs_sh_val, sirfs_normal_val, sirfs_shading_val = dataLoading.load_real_images_celebA(real_image_dataset_path, validation = True)
#real_image_mask = dataLoading.getMask(real_image_mask, global_batch_size)
#real_image, sirfs_normal, sirfs_SH, sirfs_shading, tNormal, real_image_mask, tSH, real_image_val, sirfs_sh_val, sirfs_normal_val, sirfs_shading_val, true_normal_val, mask_val, true_lighting_val = dataLoading.load_SfSNet_data(sfs_net_path, validation = True, twoLevel = True)


real_image, real_normal, real_sh, real_shading, mask, sirfs_shading, sirfs_normal, sirfs_sh, _, _,_,_, _, _,_,_  = dataLoading.load_SfSNet_data(sfs_net_path, twoLevel = True, batch_size = global_batch_size)


real_image_val, real_normal_val, real_lighting_val, real_albedo_val, mask_val, sirfs_shading_val, sirfs_normal_val, sirfs_sh_val,_,_,_,_,_,_,_,_  = dataLoading.load_SfSNet_Albedo_data(sfs_net_val_path, twoLevel = True, batch_size = global_batch_size)



# Transforms being used
#if SHOW_IMAGES:

real_image_mask_test = next(iter(mask_val))
#utils.save_image(torchvision.utils.make_grid(real_image_mask_test*255, padding=1), output_path+'val/MASK_TEST.png')

tmp = var(next(iter(syn_image1)))
tmp = denorm(tmp).data
utils.save_image(torchvision.utils.make_grid(tmp, padding=1), output_path+'val/test_synthetic_img.png')

tmp = var(next(iter(real_image_val)))
tmp = denorm(tmp)
print(tmp.data.shape)
tmp = applyMask(tmp, real_image_mask_test)
utils.save_image(torchvision.utils.make_grid(tmp.data, padding=1), output_path+'val/test_real_image.png')

tmp = var(next(iter(real_normal_val)))
tmp = denorm(tmp)
tmp = applyMask(tmp, real_image_mask_test)
utils.save_image(torchvision.utils.make_grid(tmp.data, padding=1), output_path+'val/test_real_normal.png')


tmp = var(next(iter(sirfs_normal_val)))
tmp = denorm(tmp)
tmp = applyMask(tmp, real_image_mask_test)
utils.save_image(torchvision.utils.make_grid(tmp.data, padding=1), output_path+'val/test_sirf_normal.png')

tmp = var(next(iter(sirfs_shading_val)))
#tmp = denorm(tmp)
tmp = applyMask(tmp, real_image_mask_test)
utils.save_image(torchvision.utils.make_grid(tmp.data, padding=1), output_path+'val/test_sirf_shading.png')

rImg = var(next(iter(real_image_val)))
alb = var(next(iter(real_albedo_val)))
rImg = rImg.type(dtype)
alb = alb.type(dtype)
#tmp = denorm(tmp)
print(rImg.data.max(), alb.data.max())
#shade = denorm(rImg / alb)
rImg = denorm(rImg)
alb = denorm(alb)
shade = applyMask(rImg, real_image_mask_test)
shade = shade / alb
utils.save_image(torchvision.utils.make_grid(shade.data, padding=1), output_path+'val/test_real_shading.png')


## TRUE SHADING

'''
tmp = next(iter(sirfs_shading_val))
tmp = utils.denorm(tmp)
tmp = applyMask(var(tmp).type(torch.DoubleTensor), real_image_mask_test) 
tmp = tmp.data
utils.save_image(torchvision.utils.make_grid(tmp, padding=1), output_path+'images/Validation_SIRFS_SHADING.png')
'''

featureNet = models.ResNet(models.BasicBlock, [2, 2, 2, 2], 27)
#featureNet = models.BaseSimpleFeatureNet()
lightingNet = models.LightingNet()
D = models.Discriminator()
R = models.ResNet(models.BasicBlock, [2, 2, 2, 2], 27) #
#R = models.BaseSimpleFeatureNet()

print(featureNet)
print(lightingNet)
featureNet = featureNet.cuda()
lightingNet = lightingNet.cuda()
D = D.cuda()
R = R.cuda()

dtype = torch.FloatTensor
dtype = torch.cuda.FloatTensor ## UNCOMMENT THIS LINE IF YOU'RE ON A GPU!
# Training
if load_syn:
    featureNet.load_state_dict(torch.load(output_path+'models/featureNet.pkl'))
    lightingNet.load_state_dict(torch.load(output_path+ 'models/lightingNet.pkl'))

if train_syn:
    syn_net_train(featureNet, lightingNet, syn_image1, syn_image2, syn_label, num_epochs = syn_epochs)
    # save_image(predict(featureNet, lightingNet, synVal1), outPath+'_Synthetic_Image.png')
    torch.save(featureNet.state_dict(), output_path+'models/featureNet.pkl')
    torch.save(lightingNet.state_dict(),output_path+ 'models/lightingNet.pkl')


fixed_input = var(next(iter(real_image_val))).type(dtype)
sirfs_fixed_sh = var(next(iter(sirfs_sh_val)))
sirfs_fixed_normal = var(next(iter(sirfs_normal_val)))
true_fixed_normal = var(next(iter(real_normal_val)))
true_fixed_lighting = var(next(iter(real_lighting_val)))

#real_image_mask = next(iter(real_image_mask))
#utils.show(torchvision.utils.make_grid(utils.denorm(fixed_input), padding=1))
   
if load_GAN:
    lightingNet.load_state_dict(torch.load(output_path+'models/GAN_LNet.pkl'))
    R.load_state_dict(torch.load(output_path+'models/Generator.pkl'))


if train_GAN:
    #fs = predictAllSynthetic(featureNet, syn_image1)
    if real_image_val == None:
        real_image_val = real_image
        sirfs_normal_val = sirfs_SH

    trainGAN(lightingNet, R, D, featureNet, syn_image1, real_image, sirfs_sh, fixed_input, sirfs_fixed_normal, real_image_mask_test, true_fixed_lighting, sirfs_fixed_sh, output_path = output_path, num_epoch = gan_epochs)
    torch.save(lightingNet.state_dict(), output_path+'models/GAN_LNet.pkl')
    torch.save(R.state_dict(),output_path+ 'models/Generator.pkl')


## TESTING 
fixedSH = lightingNet(R(fixed_input))
fixedSH = fixedSH.type(torch.DoubleTensor)
# print('OUTPUT OF fixedSH:', fixedSH.data.size(), sirfs_fixed_normal.size())

print('expected SH:', true_fixed_lighting)
print('predicted SH:', fixedSH)

syn_sh_out = lightingNet(featureNet(fixed_input))
syn_sh_out = syn_sh_out.type(torch.DoubleTensor)


#print(sirfs_fixed_normal)
#print(true_fixed_normal)
## With SIRFS_NORMAL
save_shading(sirfs_fixed_normal, syn_sh_out, real_image_mask_test, path = output_path+'val/', name = 'PREDICTED_SYN_SIRFS_NORMAL', shadingFromNet = True, Predicted = True)

save_shading(true_fixed_normal, syn_sh_out, real_image_mask_test, path = output_path+'val/', name = 'PREDICTED__SYN_TRUE_NORMAL', shadingFromNet = True, Predicted = True)

save_shading(sirfs_fixed_normal, fixedSH, real_image_mask_test, path = output_path+'val/', name = 'PREDICTED_SIRFS_NORMAL', shadingFromNet = True, Predicted = True)

## With True Normal
save_shading(true_fixed_normal, fixedSH, real_image_mask_test, path = output_path+'val/', name = 'PREDICTED_TRUE_NORMAL', shadingFromNet = True, Predicted = True)

## EXPECTED with SIRFS NORMAL
save_shading(sirfs_fixed_normal, true_fixed_lighting, real_image_mask_test, path = output_path+'val/', name = 'EXPECTED_SIRFS_NORMAL', shadingFromNet = True)

## EXPECTED with true normal
save_shading(true_fixed_normal, true_fixed_lighting, real_image_mask_test, path = output_path+'val/', name = 'EXPECTED_TRUE_NORMAL', shadingFromNet = True)


## Save single image
#tmp = next(iter(sirfs_shading))
#utils.save_image(tmp[0], output_path+'val/shading.png')

fSH = fixedSH.cpu().data.numpy()
tfSH = true_fixed_lighting.cpu().data.numpy()

save_results_h5(true_fixed_normal, sirfs_fixed_normal, tfSH, fSH, real_image_mask_test, output_path)

pSH = open(output_path+'predicted_sh.csv', 'a')
eSH = open(output_path+'expected_sh.csv', 'a')

for i in fSH:
    i.tofile(pSH, sep=',')
    pSH.write('\n')

for i in tfSH:
    i.tofile(eSH, sep=',')
    eSH.write('\n')

print('Generating GIF')
#generate_animation(output_path+'images/', gan_epochs,  exp_name)



'''
# Testing
if FirstRun == False:
if SHOW_IMAGES:
    dreal = next(iter(realImage))
    show(dreal[0])
    dNormal = next(iter(rNormal))
    show(denorm(dNormal[0]))
'''
'''
lightingNet = lightingNet.cpu()
D = D.cpu()
R = R.cpu()
torch.save(lightingNet.state_dict(), './CPU_GAN_LNet.pkl')
torch.save(D.state_dict(), './CPU_Discriminator.pkl')
torch.save(R.state_dict(), './CPU_Generator.pkl')
'''
