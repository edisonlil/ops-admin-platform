# Page Designer

`page_designer` owns tenant-scoped page definitions that can be designed, previewed, published, and mounted into the backend menu.

The first supported page type is `dashboard`, rendered with a grid layout in the admin UI. Future page types can extend the same page/version/schema model without creating a new bounded context for each visual shape.

Runtime code only checks that the schema exists and fails with a clear initialization error when it does not. Schema initialization remains an explicit operations step.
