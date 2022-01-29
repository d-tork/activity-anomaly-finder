"""
Dimensionality reduction with PCA.

"""
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA


def main():
    """
    Get principal components and display them along with the 
    contributions of original features to each new axis.
    """
    raw = read_data()
    features = get_numeric_features(raw)
    scaled_features = scale_data(features)
    components = get_pca_components(scaled_features)
    print(components.head().transpose().sort_values('pc1', ascending=False))


def read_data():
    df = pd.read_csv('weeklydata.csv', index_col=0)
    return df


def get_numeric_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Select only numeric features that can be scaled and transformed into 
    principal components.

    Remove what I considered to be metadata (there may be more of these) 
    and ensures that only numeric columns are selected (in case this 
    dataset changes and includes more string columns than 'user'.
    """
    drop_cols = ['user', 'week', 'excount']
    features = df.drop(columns=drop_cols)
    return features.select_dtypes(exclude=['object'])


def scale_data(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize the features prior to PCA."""
    ss = StandardScaler()
    scaled_array = ss.fit_transform(df)
    return pd.DataFrame(scaled_array, columns=df.columns)


def get_pca_components(df: pd.DataFrame) -> pd.DataFrame:
    """Get the array of new axes and the feature contributions."""
    pca = PCA()
    pca.fit(df)
    pca_labels = [f'pc{i}' for i in range(1, pca.n_components_ + 1)]
    components = pd.DataFrame(abs(pca.components_), 
            columns=df.columns,
            index=pca_labels)
    return components


if __name__ == '__main__':
    main()
