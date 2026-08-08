import numpy as np
import pytest
import tensorflow as tf

from src.models.training.losses import BinaryFocalLoss, binary_focal_loss


def test_focal_loss_is_finite_and_nonnegative():
    loss_fn = binary_focal_loss()
    y_true = tf.constant([0.0, 1.0, 0.0, 1.0])
    y_pred = tf.constant([0.1, 0.9, 0.4, 0.6])
    loss = loss_fn(y_true, y_pred).numpy()
    assert np.isfinite(loss)
    assert loss >= 0.0


def test_focal_loss_penalizes_confident_wrong_predictions_more():
    loss_fn = binary_focal_loss()
    y_true = tf.constant([1.0])
    confident_wrong = loss_fn(y_true, tf.constant([0.01])).numpy()
    confident_right = loss_fn(y_true, tf.constant([0.99])).numpy()
    assert confident_wrong > confident_right


def test_focal_loss_down_weights_easy_examples_vs_bce():
    """With gamma=0, focal loss (alpha=0.5) should be proportional to plain BCE.
    With gamma>0, the loss on an easy (well-classified) example should shrink
    relative to the gamma=0 case, which is the entire point of focal loss."""
    y_true = tf.constant([0.0])
    y_pred = tf.constant([0.05])  # easy example: predicted close to true label

    loss_gamma0 = binary_focal_loss(alpha=0.5, gamma=0.0)(y_true, y_pred).numpy()
    loss_gamma2 = binary_focal_loss(alpha=0.5, gamma=2.0)(y_true, y_pred).numpy()
    assert loss_gamma2 < loss_gamma0


def test_focal_loss_clips_extreme_predictions_without_nan():
    loss_fn = binary_focal_loss()
    y_true = tf.constant([1.0, 0.0])
    y_pred = tf.constant([0.0, 1.0])  # maximally wrong, would log(0) without clipping
    loss = loss_fn(y_true, y_pred).numpy()
    assert np.isfinite(loss)


def test_binary_focal_loss_class_matches_function():
    y_true = tf.constant([1.0, 0.0, 1.0])
    y_pred = tf.constant([0.7, 0.3, 0.2])
    fn_loss = binary_focal_loss(alpha=0.25, gamma=2.0)(y_true, y_pred).numpy()
    class_loss = BinaryFocalLoss(alpha=0.25, gamma=2.0)(y_true, y_pred).numpy()
    np.testing.assert_allclose(fn_loss, class_loss, rtol=1e-5)


def test_focal_loss_handles_keras_shape_mismatch_y_true_1d_y_pred_2d():
    """Regression test: Keras commonly passes y_true as (batch,) and y_pred as
    (batch,1) (sigmoid output). Without an explicit reshape, tf.where/tf.equal
    broadcast these into a (batch,batch) matrix instead of pairing each prediction
    with its own label -- this silently trains on garbage without raising an error
    or producing NaN, so it must be checked against a known-correct flattened result."""
    loss_fn = binary_focal_loss(alpha=0.25, gamma=2.0)

    y_true_1d = tf.constant([0.0, 1.0, 0.0, 1.0])
    y_pred_2d = tf.constant([[0.1], [0.2], [0.3], [0.9]])
    loss_mismatched_shapes = loss_fn(y_true_1d, y_pred_2d)

    y_true_2d = tf.reshape(y_true_1d, [-1, 1])
    loss_matched_shapes = loss_fn(y_true_2d, y_pred_2d)

    assert loss_mismatched_shapes.shape == ()
    np.testing.assert_allclose(loss_mismatched_shapes.numpy(), loss_matched_shapes.numpy(), rtol=1e-5)


def test_binary_focal_loss_get_config_roundtrip():
    loss = BinaryFocalLoss(alpha=0.3, gamma=1.5)
    config = loss.get_config()
    restored = BinaryFocalLoss.from_config(config)
    assert restored.alpha == 0.3
    assert restored.gamma == 1.5
