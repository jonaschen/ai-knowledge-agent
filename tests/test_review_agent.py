import unittest
from unittest.mock import MagicMock, patch
from studio.review_agent import ReviewAgent

class TestReviewAgent(unittest.TestCase):

    @patch('studio.review_agent.subprocess.run')
    @patch('studio.review_agent.Github') # 雖然我們現在依賴注入 client，但有些測試可能還是需要 mock
    def test_merge_pr_on_test_success(self, MockGithub, mock_subprocess_run):
        """
        GIVEN an open pull request
        WHEN the tests pass (returncode 0)
        THEN the agent should merge the PR.
        """
        # --- Arrange ---
        # 1. 模擬 Pytest 成功
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")
        
        # 2. 模擬 GitHub Client 和 PR
        mock_client = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.draft = False
        
        # 設定回傳鏈：client -> repo -> pulls -> pr
        # 注意：我們現在是傳入 client，所以不需要 MockGithub class 來生成 client
        mock_repo.get_pulls.return_value = [mock_pr]
        
        # 這裡不需要設定 get_repo，因為我們會在測試中直接注入依賴，
        # 或者如果您的代碼是在 process_open_prs 裡面呼叫 get_repo，那就要設定
        # 但根據最新代碼，agent 初始化後並沒有馬上 get_repo，而是由外部傳入 prs
        # 為了保險起見，我們讓 process_open_prs 可以運作
        
        # --- Act ---
        # 【修正點】使用新的建構函式：傳入 repo_path 和 github_client
        agent = ReviewAgent(repo_path="/tmp/test_repo", github_client=mock_client)
        
        # 我們直接測試 process_open_prs 邏輯，傳入我們偽造的 PR 列表
        # 因為新版邏輯是 process_open_prs(open_prs)
        agent.process_open_prs([mock_pr])
        
        # --- Assert ---
        # 驗證是否有呼叫 git checkout (代表有切換分支)
        # 注意：因為 subprocess.run 被呼叫多次，我們檢查是否有一次包含 'checkout'
        checkout_called = any('checkout' in call.args[0] for call in mock_subprocess_run.call_args_list)
        self.assertTrue(checkout_called, "Should verify git checkout is called")
        
        # 驗證是否有執行 pytest
        pytest_called = any('pytest' in str(call.args[0]) for call in mock_subprocess_run.call_args_list)
        self.assertTrue(pytest_called, "Should verify pytest is called")

        # 驗證 PR 是否被合併
        mock_pr.merge.assert_called_once()

    @patch('studio.review_agent.subprocess.run')
    def test_no_merge_on_test_failure(self, mock_subprocess_run):
        """
        GIVEN an open pull request
        WHEN the tests fail (returncode 1)
        THEN the agent should NOT merge the PR.
        """
        # --- Arrange ---
        mock_subprocess_run.return_value = MagicMock(returncode=1, stdout="Failure", stderr="Error")
        
        mock_client = MagicMock()
        mock_pr = MagicMock()
        
        # --- Act ---
        # 【修正點】同樣更新這裡
        agent = ReviewAgent(repo_path="/tmp/test_repo", github_client=mock_client)
        agent.process_open_prs([mock_pr])
        
        # --- Assert ---
        # 驗證 PR 沒有被合併
        mock_pr.merge.assert_not_called()
        
        # 驗證是否有留言 (create_issue_comment)
        # 這裡假設您的代碼會在失敗時留言，如果沒有實作留言功能，這行可以拿掉
        # mock_pr.create_issue_comment.assert_called() 

if __name__ == '__main__':
    unittest.main()
