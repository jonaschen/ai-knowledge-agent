import os
from github import Github
from dotenv import load_dotenv

def get_pr_comments():
    """
    Fetches and prints comments from a specific pull request.
    """
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPOSITORY")
    pr_number = 37  # As identified in the previous turn

    if not token or not repo_name:
        print("Error: GITHUB_TOKEN and GITHUB_REPOSITORY environment variables must be set.")
        return

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        print(f"--- Comments for PR #{pr.number}: {pr.title} ---")

        comments = pr.get_issue_comments()
        if comments.totalCount == 0:
            print("No comments found on this pull request.")
        else:
            for comment in comments:
                print(f"User: @{comment.user.login}")
                print(f"Date: {comment.created_at}")
                print("-" * 20)
                print(comment.body)
                print("=" * 40)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    get_pr_comments()
