
github actions failed:



Error: This request has been automatically failed because it uses a deprecated version of `actions/upload-artifact: v3`. Learn more: https://github.blog/changelog/2024-04-16-deprecation-notice-v3-of-the-artifact-actions/




Run poetry run pytest
============================= test session starts ==============================
platform linux -- Python 3.9.24, pytest-7.4.4, pluggy-1.6.0
rootdir: /home/runner/work/reticulum/reticulum
configfile: pytest.ini
collected 32 items

tests/test_advanced_scenarios.py F............                           [ 40%]
tests/test_exposure_scanner.py ...................                       [100%]

=================================== FAILURES ===================================
___________ TestAdvancedScenarios.test_advanced_repository_structure ___________

self = <tests.test_advanced_scenarios.TestAdvancedScenarios object at 0x7f6714a0d6a0>
advanced_test_repo = PosixPath('/home/runner/work/reticulum/reticulum/tests/advanced-test-repo')

    def test_advanced_repository_structure(self, advanced_test_repo):
        """Test that the advanced test repository has the expected structure."""
        # Check main directories
        assert (advanced_test_repo / "charts").exists()
        assert (advanced_test_repo / "dockerfiles").exists()
>       assert (advanced_test_repo / "source-code").exists()
E       AssertionError: assert False
E        +  where False = <bound method Path.exists of PosixPath('/home/runner/work/reticulum/reticulum/tests/advanced-test-repo/source-code')>()
E        +    where <bound method Path.exists of PosixPath('/home/runner/work/reticulum/reticulum/tests/advanced-test-repo/source-code')> = (PosixPath('/home/runner/work/reticulum/reticulum/tests/advanced-test-repo') / 'source-code').exists

tests/test_advanced_scenarios.py:38: AssertionError
=========================== short test summary info ============================
FAILED tests/test_advanced_scenarios.py::TestAdvancedScenarios::test_advanced_repository_structure - AssertionError: assert False
 +  where False = <bound method Path.exists of PosixPath('/home/runner/work/reticulum/reticulum/tests/advanced-test-repo/source-code')>()
 +    where <bound method Path.exists of PosixPath('/home/runner/work/reticulum/reticulum/tests/advanced-test-repo/source-code')> = (PosixPath('/home/runner/work/reticulum/reticulum/tests/advanced-test-repo') / 'source-code').exists
========================= 1 failed, 31 passed in 1.01s =========================
Error: Process completed with exit code 1.



=================================== FAILURES ===================================
___________ TestAdvancedScenarios.test_advanced_repository_structure ___________

self = <tests.test_advanced_scenarios.TestAdvancedScenarios object at 0x7facf9b4ee50>
advanced_test_repo = PosixPath('/home/runner/work/reticulum/reticulum/tests/advanced-test-repo')

    def test_advanced_repository_structure(self, advanced_test_repo):
        """Test that the advanced test repository has the expected structure."""
        # Check main directories
        assert (advanced_test_repo / "charts").exists()
        assert (advanced_test_repo / "dockerfiles").exists()
>       assert (advanced_test_repo / "source-code").exists()
E       AssertionError: assert False
E        +  where False = <bound method Path.exists of PosixPath('/home/runner/work/reticulum/reticulum/tests/advanced-test-repo/source-code')>()
E        +    where <bound method Path.exists of PosixPath('/home/runner/work/reticulum/reticulum/tests/advanced-test-repo/source-code')> = (PosixPath('/home/runner/work/reticulum/reticulum/tests/advanced-test-repo') / 'source-code').exists

tests/test_advanced_scenarios.py:38: AssertionError
=========================== short test summary info ============================
FAILED tests/test_advanced_scenarios.py::TestAdvancedScenarios::test_advanced_repository_structure - AssertionError: assert False
 +  where False = <bound method Path.exists of PosixPath('/home/runner/work/reticulum/reticulum/tests/advanced-test-repo/source-code')>()
 +    where <bound method Path.exists of PosixPath('/home/runner/work/reticulum/reticulum/tests/advanced-test-repo/source-code')> = (PosixPath('/home/runner/work/reticulum/reticulum/tests/advanced-test-repo') / 'source-code').exists
========================= 1 failed, 31 passed in 0.72s =========================
Error: Process completed with exit code 1.


