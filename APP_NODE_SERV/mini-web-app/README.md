# Mini Web Application

This is a mini web application built using Node.js and Express. The application features a homepage with a login button and a second page that contains a form.

## Project Structure

```
mini-web-app
├── src
│   ├── app.js          # Entry point of the application
│   ├── routes          # Contains route definitions
│   │   ├── home.js     # Route for the homepage
│   │   └── form.js     # Route for the form page
│   ├── views           # Contains EJS templates
│   │   ├── home.ejs    # Homepage template
│   │   └── form.ejs    # Form page template
│   └── public          # Contains static files
│       └── styles.css   # CSS styles for the application
├── package.json        # npm configuration file
└── README.md           # Project documentation
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   ```

2. Navigate to the project directory:
   ```
   cd mini-web-app
   ```

3. Install the dependencies:
   ```
   npm install
   ```

## Usage

1. Start the application:
   ```
   npm start
   ```

2. Open your browser and go to `http://localhost:3000` to view the homepage.

## Features

- Homepage with a login button
- Form page with input fields
- Basic styling with CSS

## License

This project is licensed under the MIT License.