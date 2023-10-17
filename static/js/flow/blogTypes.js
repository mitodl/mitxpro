
export type blogPost = {
  title: string,
  link: string,
  description: string,
  category: string | Array<string>,
  author: string,
  banner_image: string,
  published_date: string,
  guid: string,
}

export type Blogs = {
  posts: Array<blogPost>,
  categories: Array<string>,
}
