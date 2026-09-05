"""Offline, dev-only training script against labeled sector samples from acquired test drives; not shipped in the installer."""

from sklearn.ensemble import RandomForestClassifier


def train_provisional_classifier():
    """Dev-only training pipeline for sector classification."""
    X_train = [
        [7.5, 0.05, 1.0, 0.0],
        [7.2, 0.04, 0.0, 1.0],
        [3.0, 0.00, 0.0, 0.0],
    ]
    y_train = ["Dahua", "Hikvision", "Unknown"]

    clf = RandomForestClassifier(n_estimators=10, random_state=42)
    clf.fit(X_train, y_train)
    return clf


if __name__ == "__main__":
    train_provisional_classifier()
