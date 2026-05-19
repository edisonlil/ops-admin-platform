# Personalization

`personalization` owns per-user UI preferences such as table column visibility and display order.

The context stores preferences by tenant, user, and `view_key`. Runtime code only checks that the schema exists and fails with a clear initialization error when it does not.
