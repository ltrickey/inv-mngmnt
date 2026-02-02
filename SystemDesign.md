# System Design

#TODO: Document the data table design based on queries.  We're going to have three DynamoDB tables: 

Queries:
1. On page load: Get all of the products for all stores with all of their details 
1. When a Store is selected: Get all of the Stock from stock DB by Store ID.  hash_key/partiation_key = prod_barcode, range_key/sort_key = store_id (requirement: Secondary Index of StoreID) (TODO: Pagination?)
1. Eventually we will have CRUD operations on stock that should happen depending on sales & inventory
1. Get all of the sales from sales DB (inlude this in stock?) (Pagination)


Tables
**Products** - includes product details.  Called Scan at page load.
**Stores** - Lists store info and id.  Once a user selects a store id from the dropdown menu, we query the stock table with a Scan call on the secondary index of store_id.  We now have a list of all the product stock based on store ids
**Stock** - Lists stock information based on store_id and barcode
**Sales** - Lists sale info based on store_id and barcode.  Thought about combining this with stock, but stock will have many more writes/reads -> needs to support higher throughput.  sales will have high read but lower writes, maybe only 1/day where as stock may have 10 TPS
