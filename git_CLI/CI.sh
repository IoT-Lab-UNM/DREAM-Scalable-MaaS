# ------------------------------------------------------------
# 0) Go to your repo (any worktree is fine) and sanity-check
# ------------------------------------------------------------
cd ~/DREAM_1.3
git branch --show-current        # shows the branch checked out in THIS folder
git remote -v                    # shows all remotes (fetch/push URLs)
git worktree list                # shows all worktrees + which branch each folder has checked out


# ------------------------------------------------------------
# 1) Create a NEW branch from `digital-twin` and put it in its OWN worktree
#    (This creates branch: scalable-DIAM-MaaS, based on digital-twin)
# ------------------------------------------------------------
git worktree add -b scalable-DIAM-MaaS ../DREAM_1.3-scalable-DIAM-MaaS digital-twin

# NOTE:
# - This command both (a) creates the branch and (b) checks it out in the new folder.
# - After this, open the new folder in VSCode if you want:
#   code ../DREAM_1.3-scalable-DIAM-MaaS


# ------------------------------------------------------------
# 2) Create a separate worktree folder for `digital-twin`
#    (ONLY run this if you do NOT already have a worktree checked out to digital-twin)
# ------------------------------------------------------------
git worktree add ../DREAM_1.3-digital-twin digital-twin

# NOTE:
# - Git will fail if `digital-twin` is already checked out in another worktree.
# - Use `git worktree list` to confirm before running.


# ------------------------------------------------------------
# 3) Add a remote for the UNM/IoT-Lab repo and push the new branch there
# ------------------------------------------------------------
git remote add unmMaaS https://github.com/IoT-Lab-UNM/DREAM-Scalable-MaaS.git
git push -u unmMaaS scalable-DIAM-MaaS

# NOTE:
# - `-u` sets the upstream so later you can just run `git push` / `git pull`.
# - If GitHub prompts for password, use a PAT (token) as the “password”.


# ------------------------------------------------------------
# 4) Also push the same branch to your personal repo (origin)
# ------------------------------------------------------------
git push -u origin scalable-DIAM-MaaS

# NOTE:
# - Now this local branch can track either origin or unmMaaS (or both via explicit pushes).
# - The upstream (default push/pull) will be whichever you last set with `-u`
#   (unless you set it explicitly later).


# ------------------------------------------------------------
# 5) Check which remote the CURRENT branch is tracking (upstream remote name)
# ------------------------------------------------------------
git config --get branch.$(git branch --show-current).remote

# NOTE:
# - This prints something like: origin  OR  unmMaaS
# - To see the upstream branch too, use: git branch -vv


# ------------------------------------------------------------
# 6) Add additional remotes for other IoT-Lab repos (optional)
# ------------------------------------------------------------
git remote add unmDT https://github.com/IoT-Lab-UNM/DREAM-DigitalTwin.git
git remote add unm   https://github.com/IoT-Lab-UNM/DREAM-MeMeA.git