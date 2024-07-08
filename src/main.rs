#[macro_use]
extern crate rocket;

use rocket::response::Redirect;

mod proxy;

#[get("/")]
fn index() -> Redirect {
    Redirect::to("/forms/")
}

#[launch]
fn rocket() -> _ {
    rocket::build()
        .mount("/", routes![index])
        .mount("/", proxy::ProxyHandler)
        .manage(proxy::SecondaryServer::new())
}
