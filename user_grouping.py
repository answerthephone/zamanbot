from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from sqlalchemy import create_engine
from db import engine
import pandas as pd

N_NEIGHBORS = 10  # Seems enough, but feel free to adjust

def prepare_knn_and_aggregated_data():
    """Prepare KNN model and aggregated user transaction data for
    later use in finding relevant goal comparisons. Should be called
    every once in a while to refresh the data. (say, every 10 minutes)
    Returns the KNN model, scaled feature matrix X, and the features DataFrame."""
    transactions = pd.read_sql("SELECT * FROM transactions", engine)
    goals = pd.read_sql("SELECT * FROM financial_goals", engine)

    # Aggregate transaction data by user
    features = transactions.groupby("user_id").agg(
        expense_mean=("amount", "mean"),
        expense_std=("amount", "std"),
        transaction_count=("amount", "count"),
        most_used_currency=("currency", lambda x: x.mode()[0]),
    )
    
    # One-hot encode the most used currency
    currencies = pd.get_dummies(features["most_used_currency"], prefix="currency")
    features = pd.concat([features.drop(columns="most_used_currency"), currencies], axis=1)
    
    # Count of transactions per category
    cat_counts = (
        transactions
        .pivot_table(index="user_id", columns="category", values="amount", aggfunc="count", fill_value=0)
        .add_prefix("category_")
        .add_suffix("_count")
    )
    
    # Merge category counts into features
    features = features.merge(cat_counts, left_index=True, right_index=True, how="left")
    
    # Scale features
    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    # Fin a KNN model (+1 because the closest neighbor is the user themself - useless)
    nn = NearestNeighbors(n_neighbors=N_NEIGHBORS+1, metric="cosine")
    nn.fit(X)
    
    return nn, X, features


def find_relevant_goal_comparisons(target_user_id, nn, X, features):
    # Find the scaled feature vector for the target user
    target_index = features.index.get_loc(target_user_id)
    target_vector = X[target_index].reshape(1, -1)
    
    # Find nearest neighbors
    distances, indices = nn.kneighbors(target_vector)

    # Filter the target user himself out of the results, get similar users' feature vectors 
    similar_indices = [i for i in indices[0] if i != target_index]
    similar_users = features.index[similar_indices].to_numpy()
    
    # Gather examples of finished goals from similar users
    # Structure: (name, target_amount, currency, deadline)
    examples = []
    for similar_user_id in similar_users:
        users_goals = goals[goals["user_id"] == similar_user_id]
        finished_goals = users_goals[users_goals["finished"] == True]
        if len(finished_goals) == 0:
            continue
        for x in finished_goals[["name", "target_amount", "currency", "deadline"]].values.tolist():
            x[3] = pd.to_datetime(x[3]).date()
            examples.append(tuple(x))
    
    # Return top 3 most recent finished goals
    return sorted(examples, key=lambda x: x[3], reverse=True)[:3]
