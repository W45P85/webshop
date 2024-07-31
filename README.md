# DanShop - A Modern E-Commerce Webshop

**DanShop** is a modern e-commerce webshop currently under development. We are actively working on it daily to enhance its features and functionality. The goal is to provide an intuitive and visually appealing shopping experience.

## Live Preview

A more or less stable interim version of DanShop is available at: [https://drukober.pythonanywhere.com/](https://drukober.pythonanywhere.com/). Please note that this version may have some experimental features and is subject to ongoing changes.

## Features

- **User Profile Management:** Users can update their profiles, including personal details, email addresses, and password changes.
- **Profile Pictures:** Users can upload and display a profile picture.
- **Address Management:** Save and edit addresses, with an option to set a default address for easier management.
- **Responsive Design:** Fully responsive, optimized for all devices and screen sizes.

## Technologies

- **Django:** A powerful web framework for rapid development of web applications.
- **Bootstrap:** A modern CSS framework for responsive and engaging design.

## Installation

1. Clone the repository: `git clone <repository-url>`
2. Install dependencies: `pip install -r requirements.txt`
3. Apply migrations: `python manage.py migrate`
4. Start the server: `python manage.py runserver`


## Enhancements

### 1. Seller Templates
- Forms and data displays

### 2. Order Status Sorting
- Order status filtering
- Sorting by status
- Management views

### 3. Introducing New Order Statuses
- Pending (already included)
- Sent (already included)
- Delivered
- Cancelled

### 4. Reports and Analytics
- Sales performance reports
- Data visualization

### 5. Inventory Management
- Track product availability
- Inventory fields in `Article` model
- Views for stock levels

### 6. Order Cancellations
- Cancel orders
- Update order statuses
- Customer notifications

### 7. Customer Communication
- Messaging system
- Direct seller-customer communication
- Automated notifications

### 8. Shipping and Logistics
- Manage shipping options
- Set shipping methods and costs
- Print shipping labels
- Integrate with shipping providers

### 9. Promotions and Discounts
- Create discount codes
- Manage promotions
- Special offers and limited-time discounts

### 10. Shop Settings
- Update shop information
- Shop description and logo
- Configure payment methods

### 11. Customer Reviews
- Manage customer reviews
- Moderation capabilities
- Respond to reviews