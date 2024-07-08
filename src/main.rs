#[macro_use]
extern crate rocket;

use rocket::response::Redirect;
use rocket_db_pools::{sqlx, Database};

mod proxy;

#[derive(Database)]
#[database("db")]
struct DB(sqlx::SqlitePool);

#[get("/")]
fn index() -> Redirect {
    Redirect::to("/forms/")
}

#[launch]
fn rocket() -> _ {
    let config = rocket::Config::figment().merge((
        "databases.db.url",
        std::env::var("SQLALCHEMY_DATABASE_URI")
            .unwrap_or("sqlite:///formie.sqlite".to_string())
            .strip_prefix("sqlite:///")
            .expect("Malformed SQLALCHEMY_DATABASE_URI"),
    ));

    rocket::custom(config)
        .attach(DB::init())
        .mount("/", routes![index])
        .mount("/", proxy::ProxyHandler)
        .manage(proxy::SecondaryServer::new())
}
