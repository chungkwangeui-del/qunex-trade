"""
Deep Learning Models
Implements LSTM, GRU, and Transformer models for time series prediction
"""

import numpy as np
import pandas as pd
import logging
from typing import Tuple, Dict, List
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, Model
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, roc_auc_score


class TimeSeriesDataGenerator:
    """Generate sequences for time series models"""

    def __init__(self, sequence_length: int = 30):
        self.sequence_length = sequence_length
        self.logger = logging.getLogger(__name__)

    def create_sequences(self, X: np.ndarray, y: np.ndarray = None) -> Tuple:
        """
        Create sequences from time series data

        Args:
            X: Feature array (samples, features)
            y: Labels (optional)

        Returns:
            Tuple of (X_seq, y_seq) or just X_seq if y is None
        """
        X_seq = []
        y_seq = [] if y is not None else None

        for i in range(len(X) - self.sequence_length):
            X_seq.append(X[i:i + self.sequence_length])

            if y is not None:
                # Use the label at the end of the sequence
                y_seq.append(y[i + self.sequence_length])

        X_seq = np.array(X_seq)

        if y is not None:
            y_seq = np.array(y_seq)
            return X_seq, y_seq
        else:
            return X_seq

    def create_sequences_by_ticker(self, df: pd.DataFrame, feature_cols: List[str],
                                   target_col: str = None) -> Tuple:
        """
        Create sequences grouped by ticker

        Args:
            df: DataFrame with data
            feature_cols: List of feature column names
            target_col: Target column name (optional)

        Returns:
            Tuple of (X_seq, y_seq, tickers) or (X_seq, tickers) if target_col is None
        """
        all_X_seq = []
        all_y_seq = [] if target_col else None
        all_tickers = []

        grouped = df.groupby('ticker')

        for ticker, group in grouped:
            if len(group) < self.sequence_length + 1:
                continue

            X = group[feature_cols].values

            if target_col:
                y = group[target_col].values
                X_seq, y_seq = self.create_sequences(X, y)
                all_y_seq.extend(y_seq)
            else:
                X_seq = self.create_sequences(X)

            all_X_seq.extend(X_seq)
            all_tickers.extend([ticker] * len(X_seq))

        X_seq = np.array(all_X_seq)

        if target_col:
            y_seq = np.array(all_y_seq)
            return X_seq, y_seq, all_tickers
        else:
            return X_seq, all_tickers


class LSTMModel:
    """LSTM model for surge prediction"""

    def __init__(self, config, input_shape: Tuple, num_classes: int = 2):
        self.config = config
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.model = None
        self.logger = logging.getLogger(__name__)

    def build_model(self) -> Model:
        """Build LSTM model"""
        lstm_config = self.config['dl_models']['lstm']

        inputs = layers.Input(shape=self.input_shape)
        x = inputs

        # LSTM layers
        for i, units in enumerate(lstm_config['layers']):
            return_sequences = i < len(lstm_config['layers']) - 1
            x = layers.LSTM(
                units,
                return_sequences=return_sequences,
                dropout=lstm_config['dropout']
            )(x)
            x = layers.BatchNormalization()(x)

        # Dense layers
        x = layers.Dense(64, activation='relu')(x)
        x = layers.Dropout(lstm_config['dropout'])(x)
        x = layers.Dense(32, activation='relu')(x)

        # Output layer
        if self.num_classes == 2:
            outputs = layers.Dense(1, activation='sigmoid')(x)
            loss = 'binary_crossentropy'
        else:
            outputs = layers.Dense(self.num_classes, activation='softmax')(x)
            loss = 'sparse_categorical_crossentropy'

        model = Model(inputs=inputs, outputs=outputs)

        # Compile
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=lstm_config['learning_rate']),
            loss=loss,
            metrics=['accuracy']
        )

        self.model = model
        self.logger.info(f"LSTM model built: {model.summary()}")

        return model

    def train(self, X_train: np.ndarray, y_train: np.ndarray,
             X_val: np.ndarray, y_val: np.ndarray,
             save_path: str = 'models/lstm_best.h5') -> Dict:
        """Train LSTM model"""
        lstm_config = self.config['dl_models']['lstm']

        # Callbacks
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=self.config['training']['early_stopping_patience'],
                restore_best_weights=True
            ),
            ModelCheckpoint(
                save_path,
                monitor='val_accuracy',
                save_best_only=True,
                mode='max'
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-7
            )
        ]

        # Train
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=lstm_config['epochs'],
            batch_size=lstm_config['batch_size'],
            callbacks=callbacks,
            verbose=1
        )

        self.logger.info("LSTM training complete")

        return history.history


class GRUModel:
    """GRU model for surge prediction"""

    def __init__(self, config, input_shape: Tuple, num_classes: int = 2):
        self.config = config
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.model = None
        self.logger = logging.getLogger(__name__)

    def build_model(self) -> Model:
        """Build GRU model"""
        gru_config = self.config['dl_models']['gru']

        inputs = layers.Input(shape=self.input_shape)
        x = inputs

        # GRU layers
        for i, units in enumerate(gru_config['layers']):
            return_sequences = i < len(gru_config['layers']) - 1
            x = layers.GRU(
                units,
                return_sequences=return_sequences,
                dropout=gru_config['dropout']
            )(x)
            x = layers.BatchNormalization()(x)

        # Dense layers
        x = layers.Dense(64, activation='relu')(x)
        x = layers.Dropout(gru_config['dropout'])(x)
        x = layers.Dense(32, activation='relu')(x)

        # Output layer
        if self.num_classes == 2:
            outputs = layers.Dense(1, activation='sigmoid')(x)
            loss = 'binary_crossentropy'
        else:
            outputs = layers.Dense(self.num_classes, activation='softmax')(x)
            loss = 'sparse_categorical_crossentropy'

        model = Model(inputs=inputs, outputs=outputs)

        # Compile
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=gru_config['learning_rate']),
            loss=loss,
            metrics=['accuracy']
        )

        self.model = model
        self.logger.info(f"GRU model built")

        return model

    def train(self, X_train: np.ndarray, y_train: np.ndarray,
             X_val: np.ndarray, y_val: np.ndarray,
             save_path: str = 'models/gru_best.h5') -> Dict:
        """Train GRU model"""
        gru_config = self.config['dl_models']['gru']

        # Callbacks
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=self.config['training']['early_stopping_patience'],
                restore_best_weights=True
            ),
            ModelCheckpoint(
                save_path,
                monitor='val_accuracy',
                save_best_only=True,
                mode='max'
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-7
            )
        ]

        # Train
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=gru_config['epochs'],
            batch_size=gru_config['batch_size'],
            callbacks=callbacks,
            verbose=1
        )

        self.logger.info("GRU training complete")

        return history.history


class TransformerModel:
    """Transformer model for surge prediction"""

    def __init__(self, config, input_shape: Tuple, num_classes: int = 2):
        self.config = config
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.model = None
        self.logger = logging.getLogger(__name__)

    def transformer_encoder(self, inputs, d_model, nhead, num_layers, dropout):
        """Transformer encoder block"""
        x = inputs

        for _ in range(num_layers):
            # Multi-head attention
            attention_output = layers.MultiHeadAttention(
                num_heads=nhead,
                key_dim=d_model // nhead,
                dropout=dropout
            )(x, x)

            # Add & Norm
            x = layers.Add()([x, attention_output])
            x = layers.LayerNormalization(epsilon=1e-6)(x)

            # Feed Forward Network
            ffn = keras.Sequential([
                layers.Dense(d_model * 4, activation='relu'),
                layers.Dropout(dropout),
                layers.Dense(d_model)
            ])

            ffn_output = ffn(x)

            # Add & Norm
            x = layers.Add()([x, ffn_output])
            x = layers.LayerNormalization(epsilon=1e-6)(x)

        return x

    def build_model(self) -> Model:
        """Build Transformer model"""
        transformer_config = self.config['dl_models']['transformer']

        inputs = layers.Input(shape=self.input_shape)

        # Project to d_model dimensions
        x = layers.Dense(transformer_config['d_model'])(inputs)

        # Positional encoding
        positions = tf.range(start=0, limit=self.input_shape[0], delta=1)
        position_embeddings = layers.Embedding(
            input_dim=self.input_shape[0],
            output_dim=transformer_config['d_model']
        )(positions)
        x = x + position_embeddings

        # Transformer encoder
        x = self.transformer_encoder(
            x,
            d_model=transformer_config['d_model'],
            nhead=transformer_config['nhead'],
            num_layers=transformer_config['num_layers'],
            dropout=transformer_config['dropout']
        )

        # Global average pooling
        x = layers.GlobalAveragePooling1D()(x)

        # Dense layers
        x = layers.Dense(128, activation='relu')(x)
        x = layers.Dropout(transformer_config['dropout'])(x)
        x = layers.Dense(64, activation='relu')(x)

        # Output layer
        if self.num_classes == 2:
            outputs = layers.Dense(1, activation='sigmoid')(x)
            loss = 'binary_crossentropy'
        else:
            outputs = layers.Dense(self.num_classes, activation='softmax')(x)
            loss = 'sparse_categorical_crossentropy'

        model = Model(inputs=inputs, outputs=outputs)

        # Compile
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=transformer_config['learning_rate']),
            loss=loss,
            metrics=['accuracy']
        )

        self.model = model
        self.logger.info(f"Transformer model built")

        return model

    def train(self, X_train: np.ndarray, y_train: np.ndarray,
             X_val: np.ndarray, y_val: np.ndarray,
             save_path: str = 'models/transformer_best.h5') -> Dict:
        """Train Transformer model"""
        transformer_config = self.config['dl_models']['transformer']

        # Callbacks
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=self.config['training']['early_stopping_patience'],
                restore_best_weights=True
            ),
            ModelCheckpoint(
                save_path,
                monitor='val_accuracy',
                save_best_only=True,
                mode='max'
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-7
            )
        ]

        # Train
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=transformer_config['epochs'],
            batch_size=transformer_config['batch_size'],
            callbacks=callbacks,
            verbose=1
        )

        self.logger.info("Transformer training complete")

        return history.history


class DLModelEvaluator:
    """Evaluate deep learning models"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def evaluate(self, model: Model, X_test: np.ndarray, y_test: np.ndarray,
                model_name: str = 'model') -> Dict:
        """Evaluate deep learning model"""
        self.logger.info(f"Evaluating {model_name}...")

        # Predictions
        y_pred_proba = model.predict(X_test)

        # Convert probabilities to class predictions
        if y_pred_proba.shape[1] == 1:  # Binary
            y_pred = (y_pred_proba > 0.5).astype(int).flatten()
        else:  # Multiclass
            y_pred = np.argmax(y_pred_proba, axis=1)

        # Metrics
        accuracy = accuracy_score(y_test, y_pred)

        # ROC AUC
        try:
            if y_pred_proba.shape[1] == 1:  # Binary
                roc_auc = roc_auc_score(y_test, y_pred_proba)
            else:  # Multiclass
                roc_auc = roc_auc_score(y_test, y_pred_proba, multi_class='ovr')
        except:
            roc_auc = None

        # Classification report
        report = classification_report(y_test, y_pred, output_dict=True)

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)

        results = {
            'model_name': model_name,
            'accuracy': accuracy,
            'roc_auc': roc_auc,
            'classification_report': report,
            'confusion_matrix': cm,
            'predictions': y_pred,
            'prediction_probabilities': y_pred_proba
        }

        # Log results
        self.logger.info(f"{model_name} Results:")
        self.logger.info(f"  Accuracy: {accuracy:.4f}")
        if roc_auc:
            self.logger.info(f"  ROC AUC: {roc_auc:.4f}")
        self.logger.info(f"\nClassification Report:\n{classification_report(y_test, y_pred)}")

        return results
