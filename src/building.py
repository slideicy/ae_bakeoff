import os

import pytorch_lightning.loggers as loggers
import torch

import data
import lightning
from models import encoders, decoders, bottlenecks


def build_datamodule(model_type=None, batch_size=32, anomaly=False):
    exclude = 1 if anomaly else None
    train_size = 550 if model_type == 'classification' else None
    datamodule = data.MNISTDataModule('../data',
                                      batch_size=batch_size,
                                      train_size=train_size,
                                      exclude=exclude)

    return datamodule


def build_ae(model_type, input_shape, anomaly=False):
    latent_dim = 2 if anomaly else 20
    noise_ratio = 0.5 if model_type == 'denoising' else None
    encoder, decoder = _build_networks(model_type, input_shape, latent_dim)
    bottleneck = _build_bottleneck(model_type, latent_dim)
    ae = lightning.Autoencoder(encoder, bottleneck, decoder, lr=0.001, noise_ratio=noise_ratio)

    return ae


def _build_networks(model_type, input_shape, latent_dim):
    enc_dim = dec_dim = latent_dim
    if model_type == 'vae' or model_type.startswith('beta_vae'):
        enc_dim *= 2

    num_layers = 3
    if model_type == 'shallow':
        encoder = encoders.ShallowEncoder(input_shape, enc_dim)
        decoder = decoders.ShallowDecoder(dec_dim, input_shape)
    elif model_type == 'stacked':
        encoder = encoders.StackedEncoder(input_shape, num_layers, enc_dim)
        decoder = decoders.StackedDecoder(dec_dim, num_layers, input_shape)
    else:
        encoder = encoders.DenseEncoder(input_shape, num_layers, enc_dim)
        decoder = decoders.DenseDecoder(dec_dim, num_layers, input_shape)

    return encoder, decoder


def _build_bottleneck(model_type, latent_dim):
    if model_type == 'vanilla' or model_type == 'stacked' or model_type == 'denoising' or model_type == 'shallow':
        bottleneck = bottlenecks.IdentityBottleneck(latent_dim)
    elif model_type == 'vae':
        bottleneck = bottlenecks.VariationalBottleneck(latent_dim)
    elif model_type == 'beta_vae_strict':
        bottleneck = bottlenecks.VariationalBottleneck(latent_dim, beta=2.)
    elif model_type == 'beta_vae_loose':
        bottleneck = bottlenecks.VariationalBottleneck(latent_dim, beta=0.5)
    elif model_type == 'sparse':
        bottleneck = bottlenecks.SparseBottleneck(latent_dim, sparsity=0.25)
    elif model_type == 'vq':
        bottleneck = bottlenecks.VectorQuantizedBottleneck(latent_dim, num_categories=512)
    else:
        raise ValueError(f'Unknown model type {model_type}.')

    return bottleneck


def load_ae_from_checkpoint(model_type, input_shape, anomaly, checkpoint_path):
    checkpoint = torch.load(checkpoint_path)
    model = build_ae(model_type, input_shape, anomaly)
    model.load_state_dict(checkpoint['state_dict'])

    return model


def build_logger(model_type, task=None):
    log_dir = _get_log_dir()
    task = task or 'general'
    experiment_name = f'{model_type}_{task}'
    logger = loggers.TensorBoardLogger(log_dir, experiment_name)

    return logger


def _get_log_dir():
    script_path = os.path.dirname(__file__)
    log_dir = os.path.normpath(os.path.join(script_path, '..', 'logs'))

    return log_dir
