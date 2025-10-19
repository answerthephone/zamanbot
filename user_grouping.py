import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from sqlalchemy import text
from db import engine

N_NEIGHBORS = 10  # Seems enough, but feel free to adjust

async def prepare_knn_and_aggregated_data():
    """
    Async version — prepares KNN model and aggregated user transaction data.
    Returns the KNN model, scaled feature matrix X, and the features DataFrame.
    """
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT * FROM transactions"))
        rows = result.mappings().all()
        transactions = pd.DataFrame(rows)

    if transactions.empty:
        raise ValueError("No transactions found in database")

    # Aggregate transaction data by user
    features = transactions.groupby("user_id").agg(
        expense_mean=("amount", "mean"),
        expense_std=("amount", "std"),
        transaction_count=("amount", "count"),
        most_used_currency=("currency", lambda x: x.mode().iloc[0]),
    )

    # One-hot encode the most used currency
    currencies = pd.get_dummies(features["most_used_currency"], prefix="currency")
    features = pd.concat([features.drop(columns="most_used_currency"), currencies], axis=1)

    # Count transactions per category
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

    # Fit a KNN model (+1 because the closest neighbor is the user themself)
    nn = NearestNeighbors(n_neighbors=N_NEIGHBORS + 1, metric="cosine")
    nn.fit(X)

    return nn, X, features


async def find_relevant_goal_comparisons(target_user_id, nn, X, features):
    """
    Async version — finds relevant finished goals from similar users.
    """
    # Get target vector
    target_index = features.index.get_loc(target_user_id)
    target_vector = X[target_index].reshape(1, -1)

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT * FROM financial_goals"))
        rows = result.mappings().all()
        goals = pd.DataFrame(rows)

    if goals.empty:
        return []

    # Find nearest neighbors
    distances, indices = nn.kneighbors(target_vector)

    # Filter out the target user
    similar_indices = [i for i in indices[0] if i != target_index]
    similar_users = features.index[similar_indices].to_numpy()

    # Gather finished goals
    examples = []
    for similar_user_id in similar_users:
        users_goals = goals[goals["user_id"] == similar_user_id]
        finished_goals = users_goals[users_goals["target_amount"] <= users_goals["current_amount"]]
        if len(finished_goals) == 0:
            continue

        for x in finished_goals[["name", "target_amount", "currency", "deadline"]].values.tolist():
            x[3] = pd.to_datetime(x[3]).date()
            examples.append(tuple(x))

    # Return top 3 most recent finished goals
    return sorted(examples, key=lambda x: x[3], reverse=True)[:3]
