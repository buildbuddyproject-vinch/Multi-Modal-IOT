"""Binary focal loss -- down-weights easy (well-classified) examples so training
focuses on hard/rare ones. Chosen over plain binary cross-entropy because sepsis
onset is a rare positive class (~1.9% of windows per Step 3 EDA); without focal
loss the abundant negative windows dominate the gradient.

FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)
"""
import tensorflow as tf
import keras


def binary_focal_loss(alpha: float = 0.25, gamma: float = 2.0, epsilon: float = 1e-7):
    """Returns a loss function with the keras.losses signature (y_true, y_pred) -> scalar."""

    def loss_fn(y_true, y_pred):
        # Flatten both to 1-D: y_true commonly arrives as (batch,) while y_pred is
        # (batch, 1) (sigmoid output). Without this, tf.where/tf.equal broadcast
        # (batch,) against (batch,1) into a bogus (batch,batch) matrix -- every
        # prediction gets compared against every label instead of its own, which
        # silently produces a near-uninformative gradient (loss looks "fine" but
        # the model never learns). Always reshape before any elementwise op here.
        y_true = tf.reshape(tf.cast(y_true, tf.float32), [-1])
        y_pred = tf.reshape(tf.clip_by_value(y_pred, epsilon, 1.0 - epsilon), [-1])

        p_t = tf.where(tf.equal(y_true, 1.0), y_pred, 1.0 - y_pred)
        alpha_t = tf.where(tf.equal(y_true, 1.0), alpha, 1.0 - alpha)

        focal_weight = alpha_t * tf.pow(1.0 - p_t, gamma)
        loss = -focal_weight * tf.math.log(p_t)
        return tf.reduce_mean(loss)

    loss_fn.__name__ = f"binary_focal_loss_a{alpha}_g{gamma}"
    return loss_fn


@keras.saving.register_keras_serializable(package="sepsis_model")
class BinaryFocalLoss(keras.losses.Loss):
    """Class form (serializable in saved models) wrapping the same computation."""

    def __init__(self, alpha: float = 0.25, gamma: float = 2.0, epsilon: float = 1e-7, name: str = "binary_focal_loss", **kwargs):
        super().__init__(name=name, **kwargs)
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon

    def call(self, y_true, y_pred):
        return binary_focal_loss(self.alpha, self.gamma, self.epsilon)(y_true, y_pred)

    def get_config(self):
        config = super().get_config()
        config.update({"alpha": self.alpha, "gamma": self.gamma, "epsilon": self.epsilon})
        return config
